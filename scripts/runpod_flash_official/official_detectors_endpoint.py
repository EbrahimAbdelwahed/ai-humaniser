from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import importlib.util
from pathlib import Path
from typing import Any

from runpod_flash import Endpoint, GpuGroup


ENDPOINT_NAME = "academic-engine-official-detectors-v1"
MAX_TEXT_BYTES = 9_500_000
DEFAULT_TIMEOUT_SECONDS = 900
BOOTSTRAP_ROOT = Path(os.environ.get("OFFICIAL_DETECTOR_BOOTSTRAP_ROOT", "/tmp/academic_engine_official_detectors"))
BOOTSTRAP_TIMEOUT_SECONDS = int(os.environ.get("OFFICIAL_DETECTOR_BOOTSTRAP_TIMEOUT_SECONDS", "600"))


@Endpoint(
    name=ENDPOINT_NAME,
    gpu=[GpuGroup.ADA_24, GpuGroup.AMPERE_24, GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=30,
    execution_timeout_ms=DEFAULT_TIMEOUT_SECONDS * 1000,
    dependencies=[],
)
async def detect(data: dict | None = None, **kwargs):
    data = _normalize_input(data, kwargs)
    operation = str(data.get("operation") or data.get("detector") or "score_batch").lower()
    if operation == "health":
        return _health()
    if operation == "model_inventory":
        return _model_inventory()
    if operation == "bootstrap":
        return _bootstrap_runtime(data)
    if operation == "score_batch":
        return _score_batch(data)
    return _score_single_request(data)


def _normalize_input(data: dict | None, kwargs: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data or {})
    payload.update(kwargs)
    return payload


def _health() -> dict[str, Any]:
    return {
        "available": True,
        "operation": "health",
        "endpoint": ENDPOINT_NAME,
        "runpod_flash_imported": True,
        "gpu_policy": {
            "default_gpu": ["ADA_24", "AMPERE_24", "AMPERE_16"],
            "workers": [0, 1],
            "idle_timeout_seconds": 30,
            "avoids_default_80gb_gpu": True,
            "reason": "Use smaller same-tokenizer model pairs on 24GB for iterative calibration; Falcon-7B default requires 48GB.",
        },
        "profiles": {
            "stable": ["official_binoculars"],
            "calibration": ["official_binoculars", "official_fast_detectgpt"],
            "research": ["official_binoculars", "official_fast_detectgpt"],
        },
        "supported_detectors": ["official_binoculars", "official_fast_detectgpt"],
        "unsupported_runtime_notes": {
            "official_ghostbuster": (
                "Official Ghostbuster requires a local repo and OPENAI_API_KEY. "
                "This endpoint documents that requirement and does not execute Ghostbuster unless OPENAI_API_KEY is present."
            )
        },
        "env": {
            "binoculars_repo_configured": bool(os.environ.get("BINOCULARS_REPO")),
            "fast_detectgpt_repo_configured": bool(os.environ.get("FAST_DETECTGPT_REPO")),
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
            "bootstrap_root": str(BOOTSTRAP_ROOT),
            "runtime_bootstrap_default": True,
        },
    }


def _model_inventory() -> dict[str, Any]:
    return {
        "available": True,
        "operation": "model_inventory",
        "official_binoculars": {
            "wrapper": str(_wrapper_path("binoculars_official_cli.py")),
            "repo_env": "BINOCULARS_REPO",
            "repo_required": False,
            "default_observer_model": "tiiuae/falcon-7b",
            "default_performer_model": "tiiuae/falcon-7b-instruct",
        },
        "official_fast_detectgpt": {
            "wrapper": str(_wrapper_path("fast_detectgpt_official_cli.py")),
            "repo_env": "FAST_DETECTGPT_REPO",
            "repo_required": True,
            "default_sampling_model": "gpt-neo-2.7B",
            "default_scoring_model": "gpt-neo-2.7B",
        },
        "official_ghostbuster": {
            "executed": False,
            "requires_openai_api": True,
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
            "model_selection_note": (
                "Official Ghostbuster uses its original OpenAI logprob-based feature extraction path. "
                "DeepSeek cannot be substituted unless a separate compatible logprob feature adapter is implemented."
            ),
        },
    }


def _bootstrap_runtime(data: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    detectors = _expand_detectors(data.get("detectors") or [data.get("profile") or "stable"])
    results = {}
    for detector in detectors:
        if detector == "official_binoculars":
            results[detector] = _bootstrap_binoculars()
        elif detector == "official_fast_detectgpt":
            results[detector] = _bootstrap_fast_detectgpt()
        elif detector in {"official_ghostbuster", "ghostbuster_official"}:
            results[detector] = _ghostbuster_not_executed()
        else:
            results[detector] = _unavailable(detector, "unsupported_detector", f"Unsupported detector: {detector}")
    return {
        "available": all(bool(result.get("available")) for result in results.values()) if results else False,
        "operation": "bootstrap",
        "profile": str(data.get("profile") or "stable"),
        "results": results,
        "timing": {"total_seconds": round(time.perf_counter() - started, 4)},
    }


def _score_single_request(data: dict[str, Any]) -> dict[str, Any]:
    detector = _normalize_detector_name(str(data.get("detector") or "official_binoculars"))
    text = str(data.get("text") or "")
    return _score_detector(detector, data, text)


def _score_batch(data: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    texts = data.get("texts") or []
    if not isinstance(texts, list):
        return {
            "available": False,
            "failure_mode": "bad_request",
            "error": "`texts` must be a list of objects with `id` and `text`.",
        }
    detectors = _expand_detectors(data.get("detectors") or [data.get("profile") or "stable"])
    results = []
    errors = []
    for index, item in enumerate(texts):
        if not isinstance(item, dict):
            item = {"id": str(index), "text": str(item)}
        item_id = str(item.get("id") or item.get("candidate_id") or index)
        text = str(item.get("text") or "")
        signals = []
        raw = {}
        for detector in detectors:
            output = _score_detector(detector, data, text)
            raw[detector] = output
            if not output.get("available"):
                errors.append(
                    {
                        "scope": "detector",
                        "detector": detector,
                        "item_id": item_id,
                        "failure_mode": output.get("failure_mode") or "detector_unavailable",
                        "message": str(output.get("error") or "detector unavailable"),
                    }
                )
            signals.append(_signal_from_output(detector, output))
        available_scores = [signal["score"] for signal in signals if signal["available"]]
        artificiality_risk = sum(available_scores) / len(available_scores) if available_scores else 0.0
        results.append(
            {
                "id": item_id,
                "candidate_id": item.get("candidate_id"),
                "signals": signals,
                "raw_detector_results": raw,
                "artificiality_risk": round(artificiality_risk, 4),
                "warnings": [f"{signal['detector']} unavailable" for signal in signals if not signal["available"]],
            }
        )
    return {
        "request_id": str(data.get("request_id") or ""),
        "profile": str(data.get("profile") or "stable"),
        "results": results,
        "errors": errors,
        "timing": {"total_seconds": round(time.perf_counter() - started, 4), "batch_size": len(texts)},
    }


def _expand_detectors(detectors: Any) -> list[str]:
    expanded = []
    for detector in detectors:
        name = _normalize_detector_name(str(detector))
        if name == "stable":
            expanded.append("official_binoculars")
        elif name in {"calibration", "research"}:
            expanded.extend(["official_binoculars", "official_fast_detectgpt"])
        else:
            expanded.append(name)
    return list(dict.fromkeys(expanded))


def _normalize_detector_name(name: str) -> str:
    normalized = name.lower().strip().replace("-", "_")
    aliases = {
        "binoculars": "official_binoculars",
        "binoculars_official": "official_binoculars",
        "fast_detectgpt": "official_fast_detectgpt",
        "fast_detect_gpt": "official_fast_detectgpt",
        "official_fast_detect_gpt": "official_fast_detectgpt",
    }
    return aliases.get(normalized, normalized)


def _score_detector(detector: str, data: dict[str, Any], text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        return _unavailable(detector, "payload_too_large", "Payload exceeds safe 10MB RunPod Flash limit.")
    if not text.strip():
        return _unavailable(detector, "empty_text", "Empty text cannot be scored.")
    if detector == "official_binoculars":
        return _official_binoculars(data, text)
    if detector == "official_fast_detectgpt":
        return _official_fast_detectgpt(data, text)
    if detector in {"official_ghostbuster", "ghostbuster_official"}:
        return _ghostbuster_not_executed()
    return _unavailable(detector, "unsupported_detector", f"Unsupported detector: {detector}")


def _official_binoculars(data: dict[str, Any], text: str) -> dict[str, Any]:
    command = [sys.executable, str(_wrapper_path("binoculars_official_cli.py"))]
    repo = str(data.get("binoculars_repo") or os.environ.get("BINOCULARS_REPO") or "")
    if not repo and _bootstrap_enabled(data) and not _module_available("binoculars"):
        bootstrap = _bootstrap_binoculars()
        if not bootstrap["available"]:
            return bootstrap
        repo = str(bootstrap.get("repo") or "")
    if repo:
        command.extend(["--repo", repo])
    command.extend(
        [
            "--observer-model",
            str(data.get("observer_model") or "tiiuae/falcon-7b"),
            "--performer-model",
            str(data.get("performer_model") or "tiiuae/falcon-7b-instruct"),
            "--mode",
            str(data.get("mode") or "low-fpr"),
            "--max-token-observed",
            str(int(data.get("max_token_observed") or 512)),
        ]
    )
    if bool(data.get("offline", False)):
        command.append("--offline")
    if bool(data.get("no_bfloat16", False)):
        command.append("--no-bfloat16")
    return _run_official_wrapper("official_binoculars", command, text, int(data.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS))


def _official_fast_detectgpt(data: dict[str, Any], text: str) -> dict[str, Any]:
    repo = Path(str(data.get("fast_detectgpt_repo") or os.environ.get("FAST_DETECTGPT_REPO") or ""))
    if not str(repo) or not (repo / "scripts" / "local_infer.py").exists():
        if _bootstrap_enabled(data):
            bootstrap = _bootstrap_fast_detectgpt()
            if not bootstrap["available"]:
                return bootstrap
            repo = Path(str(bootstrap["repo"]))
        else:
            return _unavailable(
                "official_fast_detectgpt",
                "model_assets_missing",
                "FAST_DETECTGPT_REPO must point to a local baoguangsheng/fast-detect-gpt clone with scripts/local_infer.py.",
            )
    command = [
        sys.executable,
        str(_wrapper_path("fast_detectgpt_official_cli.py")),
        "--repo",
        str(repo),
        "--sampling-model-name",
        str(data.get("sampling_model_name") or "gpt-neo-2.7B"),
        "--scoring-model-name",
        str(data.get("scoring_model_name") or "gpt-neo-2.7B"),
        "--device",
        str(data.get("device") or "cuda"),
    ]
    cache_dir = data.get("cache_dir") or os.environ.get("FAST_DETECTGPT_CACHE_DIR")
    if cache_dir:
        command.extend(["--cache-dir", str(cache_dir)])
    if bool(data.get("offline", False)):
        command.append("--offline")
    return _run_official_wrapper("official_fast_detectgpt", command, text, int(data.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS))


def _bootstrap_enabled(data: dict[str, Any]) -> bool:
    if "runtime_bootstrap" in data:
        return bool(data.get("runtime_bootstrap"))
    return os.environ.get("OFFICIAL_DETECTOR_RUNTIME_BOOTSTRAP", "1").strip().lower() not in {"0", "false", "no", "off"}


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _bootstrap_binoculars() -> dict[str, Any]:
    BOOTSTRAP_ROOT.mkdir(parents=True, exist_ok=True)
    repo = BOOTSTRAP_ROOT / "Binoculars"
    if not (repo / "binoculars" / "detector.py").exists():
        clone = _run_bootstrap_command(
            "official_binoculars",
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/ahans30/Binoculars.git",
                str(repo),
            ],
            "model_assets_missing",
        )
        if not clone["available"]:
            return clone
    deps = _run_bootstrap_command(
        "official_binoculars",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "transformers>=4.40",
            "accelerate",
            "sentencepiece",
            "protobuf",
            "numpy",
        ],
        "dependency_missing",
    )
    if not deps["available"]:
        return deps
    install = _run_bootstrap_command(
        "official_binoculars",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(repo),
        ],
        "dependency_missing",
    )
    if not install["available"]:
        return install
    return {"available": True, "repo": str(repo)}


def _bootstrap_fast_detectgpt() -> dict[str, Any]:
    BOOTSTRAP_ROOT.mkdir(parents=True, exist_ok=True)
    repo = BOOTSTRAP_ROOT / "fast-detect-gpt"
    if not (repo / "scripts" / "local_infer.py").exists():
        clone = _run_bootstrap_command(
            "official_fast_detectgpt",
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/baoguangsheng/fast-detect-gpt.git",
                str(repo),
            ],
            "model_assets_missing",
        )
        if not clone["available"]:
            return clone
    install_modern = _run_bootstrap_command(
        "official_fast_detectgpt",
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "transformers>=4.40",
            "scipy",
            "numpy",
            "tqdm",
        ],
        "dependency_missing",
    )
    if not install_modern["available"]:
        return install_modern
    requirements = repo / "requirements.txt"
    if requirements.exists() and os.environ.get("OFFICIAL_DETECTOR_INSTALL_REQUIREMENTS", "0").strip().lower() in {"1", "true", "yes", "on"}:
        install = _run_bootstrap_command(
            "official_fast_detectgpt",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements),
            ],
            "dependency_missing",
        )
        if not install["available"]:
            return install
    return {"available": True, "repo": str(repo)}


def _run_bootstrap_command(detector: str, command: list[str], failure_mode: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=BOOTSTRAP_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _unavailable(detector, "bootstrap_timeout", f"Runtime bootstrap exceeded {BOOTSTRAP_TIMEOUT_SECONDS}s.")
    except Exception as error:
        return _unavailable(detector, "bootstrap_failed", str(error))
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        return _unavailable(
            detector,
            failure_mode,
            stderr[-1200:] or stdout[-1200:] or f"Runtime bootstrap command failed with exit {completed.returncode}.",
        )
    return {"available": True}


def _ghostbuster_not_executed() -> dict[str, Any]:
    if os.environ.get("OPENAI_API_KEY"):
        return _unavailable(
            "official_ghostbuster",
            "unsupported_detector",
            "Official Ghostbuster is documented here but intentionally not executed by this cost-aware endpoint.",
        )
    return _unavailable(
        "official_ghostbuster",
        "api_key_missing",
        "Official Ghostbuster requires OPENAI_API_KEY and is not executed unless that key is present.",
    )


def _run_official_wrapper(detector: str, command: list[str], text: str, timeout_seconds: int) -> dict[str, Any]:
    wrapper = Path(command[1])
    if not wrapper.exists():
        return _unavailable(detector, "wrapper_missing", f"Official wrapper not found: {wrapper}")
    try:
        completed = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _unavailable(detector, "timeout", f"{detector} exceeded {timeout_seconds}s timeout.")
    except Exception as error:
        return _unavailable(detector, "execution_failed", str(error))
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        failure_mode = "detector_unavailable"
        lowered = stderr.lower()
        if "import failed" in lowered or "no module named" in lowered:
            failure_mode = "dependency_missing"
        elif "not found" in lowered or "repo" in lowered:
            failure_mode = "model_assets_missing"
        return _unavailable(detector, failure_mode, stderr or completed.stdout.strip() or f"{detector} failed.")
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return _unavailable(detector, "invalid_output", f"Could not parse wrapper JSON: {error}")
    score = _clamp(float(raw.get("score", 0.0)))
    raw.update(
        {
            "available": True,
            "detector": detector,
            "score": round(score, 4),
            "confidence": _clamp(float(raw.get("confidence", 0.0))),
            "label": str(raw.get("label") or _label(score)),
            "failure_mode": None,
        }
    )
    return raw


def _signal_from_output(detector: str, output: dict[str, Any]) -> dict[str, Any]:
    return {
        "detector": detector,
        "available": bool(output.get("available", False)),
        "score": _clamp(float(output.get("score") or 0.0)),
        "confidence": _clamp(float(output.get("confidence") or 0.0)),
        "label": str(output.get("label") or ("unavailable" if not output.get("available") else _label(float(output.get("score") or 0.0)))),
        "raw_result": output,
        "error": output.get("error"),
        "failure_mode": output.get("failure_mode"),
    }


def _unavailable(detector: str, failure_mode: str, error: str) -> dict[str, Any]:
    return {
        "available": False,
        "detector": detector,
        "score": 0.0,
        "confidence": 0.0,
        "label": "unavailable",
        "failure_mode": failure_mode,
        "error": error,
    }


def _label(score: float) -> str:
    return "elevated_risk" if score >= 0.62 else "moderate_risk" if score >= 0.38 else "lower_risk"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _wrapper_path(filename: str) -> Path:
    local_wrapper = Path(__file__).resolve().parent / "official_wrappers" / filename
    if local_wrapper.exists():
        return local_wrapper
    return Path(__file__).resolve().parents[1] / "official" / filename


if __name__ == "__main__":
    print(json.dumps(_health(), indent=2))
