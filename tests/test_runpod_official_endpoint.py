from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts.runpod_flash_official import official_detectors_endpoint as endpoint


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "scripts" / "runpod_flash_official" / "README.md"


def test_official_endpoint_health_documents_cost_controls_and_ghostbuster(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    health = endpoint._health()

    assert health["gpu_policy"]["default_gpu"] == ["ADA_24", "AMPERE_24", "AMPERE_16"]
    assert health["gpu_policy"]["workers"] == [0, 1]
    assert health["gpu_policy"]["avoids_default_80gb_gpu"] is True
    assert "official_ghostbuster" in health["unsupported_runtime_notes"]
    assert health["env"]["openai_api_key_present"] is False


def test_official_flash_readme_documents_code_only_runtime_bootstrap_contract():
    readme = README.read_text()

    assert "flash build --no-deps --exclude torch,torchvision,torchaudio,numpy,scipy,scikit-learn,sklearn,transformers,accelerate,sentencepiece,protobuf" in readme
    assert "artifact under the RunPod Flash 500MB limit" in readme
    assert "code-only artifact" in readme
    assert "Runtime Bootstrap" in readme
    assert "OFFICIAL_DETECTOR_RUNTIME_BOOTSTRAP=1" in readme
    assert "controlled calibration aid" in readme
    assert "fail explicitly" in readme


def test_official_endpoint_batch_returns_explicit_unavailable_for_missing_fast_detectgpt_repo(monkeypatch):
    monkeypatch.delenv("FAST_DETECTGPT_REPO", raising=False)

    result = endpoint._score_batch(
        {
            "profile": "calibration",
            "texts": [{"id": "candidate-1", "text": "A short academic sentence."}],
            "detectors": ["official_fast_detectgpt"],
            "runtime_bootstrap": False,
        }
    )

    signal = result["results"][0]["signals"][0]
    assert signal["detector"] == "official_fast_detectgpt"
    assert signal["available"] is False
    assert signal["failure_mode"] == "model_assets_missing"
    assert result["errors"][0]["failure_mode"] == "model_assets_missing"


def test_official_endpoint_bootstrap_operation_reports_detector_results(monkeypatch):
    monkeypatch.setattr(endpoint, "_bootstrap_binoculars", lambda: {"available": True, "repo": "/tmp/Binoculars"})
    monkeypatch.setattr(endpoint, "_bootstrap_fast_detectgpt", lambda: {"available": False, "failure_mode": "model_assets_missing"})

    result = endpoint._bootstrap_runtime({"detectors": ["official_binoculars", "official_fast_detectgpt"]})

    assert result["operation"] == "bootstrap"
    assert result["available"] is False
    assert result["results"]["official_binoculars"]["available"] is True
    assert result["results"]["official_fast_detectgpt"]["failure_mode"] == "model_assets_missing"


def test_official_endpoint_returns_explicit_unavailable_for_missing_wrapper():
    result = endpoint._run_official_wrapper(
        "official_binoculars",
        [endpoint.sys.executable, "/missing/binoculars_official_cli.py"],
        "A short academic sentence.",
        5,
    )

    assert result["available"] is False
    assert result["failure_mode"] == "wrapper_missing"


def test_official_endpoint_ghostbuster_mentions_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = endpoint._score_detector("official_ghostbuster", {}, "Some text.")

    assert result["available"] is False
    assert result["failure_mode"] == "api_key_missing"
    assert "OPENAI_API_KEY" in result["error"]


def test_official_endpoint_normalizes_successful_wrapper_output(monkeypatch):
    completed = SimpleNamespace(
        returncode=0,
        stdout=json.dumps({"score": 1.7, "confidence": 0.8, "label": "elevated_risk"}),
        stderr="",
    )
    monkeypatch.setattr(endpoint.subprocess, "run", lambda *args, **kwargs: completed)

    result = endpoint._run_official_wrapper(
        "official_binoculars",
        [endpoint.sys.executable, str(endpoint._wrapper_path("binoculars_official_cli.py"))],
        "Some text.",
        5,
    )

    assert result["available"] is True
    assert result["detector"] == "official_binoculars"
    assert result["score"] == 1.0
    assert result["failure_mode"] is None


def test_official_endpoint_prefers_packaged_runpod_wrapper():
    wrapper = endpoint._wrapper_path("binoculars_official_cli.py")

    assert "scripts/runpod_flash_official/official_wrappers/binoculars_official_cli.py" in str(wrapper)
    assert wrapper.exists()


def test_official_endpoint_wrapper_failure_modes_are_explicit(monkeypatch):
    cases = [
        ("Import failed: No module named 'torch'", "dependency_missing"),
        ("repo not found at /models/fast-detect-gpt", "model_assets_missing"),
        ("unexpected detector failure", "detector_unavailable"),
    ]

    for stderr, expected_failure_mode in cases:
        completed = SimpleNamespace(returncode=1, stdout="", stderr=stderr)
        monkeypatch.setattr(endpoint.subprocess, "run", lambda *args, **kwargs: completed)

        result = endpoint._run_official_wrapper(
            "official_binoculars",
            [endpoint.sys.executable, str(endpoint._wrapper_path("binoculars_official_cli.py"))],
            "Some text.",
            5,
        )

        assert result["available"] is False
        assert result["failure_mode"] == expected_failure_mode
