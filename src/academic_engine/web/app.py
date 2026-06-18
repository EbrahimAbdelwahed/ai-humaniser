from __future__ import annotations

import hashlib
import os
import time
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from academic_engine.config import EngineConfig, load_env_file
from academic_engine.detectors import detector_providers_from_config
from academic_engine.pipeline import AcademicRewritePipeline
from academic_engine.schemas import DetectorResult, SemanticRepresentation
from academic_engine.scoring import detector_consensus, score_candidate

try:  # FastAPI is an optional web extra.
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover - exercised only without web extras installed.
    FastAPI = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]
    HTMLResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]


DetectorPreset = Literal[
    "local",
    "local+fast-detectgpt",
    "local+official",
    "official-fast-detectgpt",
]
DetectorExecution = Literal["sequential", "parallel"]
JobKind = Literal["detect", "refine"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]
STATIC_DIR = Path(__file__).parent / "static"


class DetectRequest(BaseModel):
    text: str = Field(min_length=1)
    detectors: DetectorPreset = "local"
    detector_execution: DetectorExecution = "sequential"


class RefineRequest(DetectRequest):
    cycles: int = Field(default=1, ge=1, le=2)
    mock_provider: bool | None = None


@dataclass(frozen=True)
class RemotePolicyDecision:
    requested: bool
    allowed: bool
    reserved: bool = False
    fallback_to_local: bool = False
    warnings: tuple[str, ...] = ()


@dataclass
class WebRunContext:
    client_id: str = "anonymous"
    remote_decision: RemotePolicyDecision = field(default_factory=lambda: RemotePolicyDecision(False, False))
    remote_state: "RemoteEndpointState | None" = None
    settings: "WebSettings | None" = None

    @property
    def policy_warnings(self) -> list[str]:
        return list(self.remote_decision.warnings)


@dataclass
class JobRecord:
    job_id: str
    kind: JobKind
    status: JobStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    future: Future | None = None
    request: DetectRequest | RefineRequest | None = None
    context: WebRunContext = field(default_factory=WebRunContext)

    def public(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "result": self.result,
        }


class WebSettings(BaseModel):
    max_words: int = Field(default=4000, ge=25, le=25000)
    workers: int = Field(default=1, ge=1, le=4)
    inline_jobs: bool = False
    remote_detectors_enabled: bool = True
    remote_max_words: int = Field(default=1200, ge=25, le=25000)
    remote_global_daily_limit: int = Field(default=100, ge=0, le=100000)
    remote_per_client_daily_limit: int = Field(default=5, ge=0, le=10000)
    remote_min_interval_seconds: int = Field(default=10, ge=0, le=3600)
    remote_cache_ttl_seconds: int = Field(default=604800, ge=0, le=2_592_000)
    remote_max_concurrent_jobs: int = Field(default=1, ge=0, le=16)

    @classmethod
    def from_env(cls) -> "WebSettings":
        file_values = load_env_file()

        def env_int(name: str, default: int, lower: int, upper: int) -> int:
            try:
                value = int(os.getenv(name) or file_values.get(name, str(default)))
            except ValueError:
                value = default
            return max(lower, min(upper, value))

        def env_bool(name: str, default: bool) -> bool:
            value = os.getenv(name) or file_values.get(name)
            if value is None:
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            max_words=env_int("ACADEMIC_ENGINE_WEB_MAX_WORDS", 4000, 25, 25000),
            workers=env_int("ACADEMIC_ENGINE_WEB_WORKERS", 1, 1, 4),
            inline_jobs=env_bool("ACADEMIC_ENGINE_WEB_INLINE_JOBS", bool(os.getenv("VERCEL"))),
            remote_detectors_enabled=env_bool("ACADEMIC_ENGINE_ENABLE_REMOTE_DETECTORS", True),
            remote_max_words=env_int("ACADEMIC_ENGINE_REMOTE_MAX_WORDS", 1200, 25, 25000),
            remote_global_daily_limit=env_int("ACADEMIC_ENGINE_REMOTE_DAILY_LIMIT", 100, 0, 100000),
            remote_per_client_daily_limit=env_int("ACADEMIC_ENGINE_REMOTE_PER_IP_DAILY_LIMIT", 5, 0, 10000),
            remote_min_interval_seconds=env_int("ACADEMIC_ENGINE_REMOTE_MIN_INTERVAL_SECONDS", 10, 0, 3600),
            remote_cache_ttl_seconds=env_int("ACADEMIC_ENGINE_REMOTE_CACHE_TTL_HOURS", 168, 0, 720) * 3600,
            remote_max_concurrent_jobs=env_int("ACADEMIC_ENGINE_REMOTE_MAX_CONCURRENT_JOBS", 1, 0, 16),
        )


class RemoteEndpointState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.daily_key = self._today_key()
        self.global_daily_count = 0
        self.client_daily_counts: dict[str, int] = {}
        self.client_last_remote_at: dict[str, float] = {}
        self.active_remote_jobs = 0

    def evaluate_and_reserve(
        self,
        *,
        settings: WebSettings,
        request: DetectRequest | RefineRequest,
        client_id: str,
        fast_configured: bool,
    ) -> RemotePolicyDecision:
        if not remote_requested(request.detectors):
            return RemotePolicyDecision(requested=False, allowed=False)

        warnings: list[str] = []
        words = len(request.text.split())
        if not settings.remote_detectors_enabled:
            warnings.append("Remote detector policy disabled Fast-DetectGPT; local diagnostic completed.")
            return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
        if not fast_configured:
            warnings.append("Fast-DetectGPT is not configured; local diagnostic completed.")
            return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
        if words > settings.remote_max_words:
            warnings.append(
                f"Remote detector skipped because the input has {words} words; remote limit is {settings.remote_max_words}. "
                "Local diagnostic completed."
            )
            return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))

        now = time.time()
        today = self._today_key()
        with self.lock:
            self._roll_daily_window(today)
            if settings.remote_max_concurrent_jobs == 0:
                warnings.append("Remote detector policy currently allows no concurrent remote jobs; local diagnostic completed.")
                return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
            if self.active_remote_jobs >= settings.remote_max_concurrent_jobs:
                warnings.append("Remote detector capacity is busy; local diagnostic completed.")
                return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
            if self.global_daily_count >= settings.remote_global_daily_limit:
                warnings.append("Remote detector daily budget reached; local diagnostic completed.")
                return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
            client_count = self.client_daily_counts.get(client_id, 0)
            if client_count >= settings.remote_per_client_daily_limit:
                warnings.append("Remote detector daily limit reached for this client; local diagnostic completed.")
                return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))
            last_remote_at = self.client_last_remote_at.get(client_id)
            if last_remote_at is not None and now - last_remote_at < settings.remote_min_interval_seconds:
                wait_seconds = max(1, int(settings.remote_min_interval_seconds - (now - last_remote_at)))
                warnings.append(f"Remote detector throttled for this client; retry in about {wait_seconds}s. Local diagnostic completed.")
                return RemotePolicyDecision(True, False, fallback_to_local=True, warnings=tuple(warnings))

            self.global_daily_count += 1
            self.client_daily_counts[client_id] = client_count + 1
            self.client_last_remote_at[client_id] = now
            self.active_remote_jobs += 1
        return RemotePolicyDecision(True, True, reserved=True)

    def release_remote_job(self) -> None:
        with self.lock:
            self.active_remote_jobs = max(0, self.active_remote_jobs - 1)

    def get_cached(self, key: str) -> DetectorResult | None:
        now = time.time()
        with self.lock:
            cached = self.cache.get(key)
            if cached is None:
                return None
            expires_at, payload = cached
            if expires_at <= now:
                self.cache.pop(key, None)
                return None
        result = DetectorResult.model_validate(payload)
        raw = dict(result.raw_result)
        raw["web_cache_hit"] = True
        raw["web_cache_key"] = key
        return result.model_copy(update={"raw_result": raw, "checked_at": datetime.now(timezone.utc)})

    def set_cached(self, key: str, result: DetectorResult, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        raw = dict(result.raw_result)
        raw["web_cache_hit"] = False
        raw["web_cache_key"] = key
        cacheable = result.model_copy(update={"raw_result": raw})
        with self.lock:
            self.cache[key] = (time.time() + ttl_seconds, cacheable.model_dump(mode="json"))

    def public(self, settings: WebSettings) -> dict[str, Any]:
        today = self._today_key()
        with self.lock:
            self._roll_daily_window(today)
            return {
                "enabled": settings.remote_detectors_enabled,
                "max_words": settings.remote_max_words,
                "daily_limit": settings.remote_global_daily_limit,
                "per_client_daily_limit": settings.remote_per_client_daily_limit,
                "min_interval_seconds": settings.remote_min_interval_seconds,
                "cache_ttl_seconds": settings.remote_cache_ttl_seconds,
                "max_concurrent_jobs": settings.remote_max_concurrent_jobs,
                "active_remote_jobs": self.active_remote_jobs,
                "global_daily_used": self.global_daily_count,
                "cache_entries": len(self.cache),
            }

    def _roll_daily_window(self, today: str) -> None:
        if self.daily_key == today:
            return
        self.daily_key = today
        self.global_daily_count = 0
        self.client_daily_counts = {}
        self.client_last_remote_at = {}

    @staticmethod
    def _today_key() -> str:
        return datetime.now(timezone.utc).date().isoformat()


class CachedRemoteDetectorProvider:
    def __init__(self, *, provider, state: RemoteEndpointState, settings: WebSettings, route_key: str) -> None:
        self.provider = provider
        self.provider_name = provider.provider_name
        self.state = state
        self.settings = settings
        self.route_key = route_key

    def analyze(self, text: str) -> DetectorResult:
        key = remote_cache_key(text=text, provider_name=self.provider_name, route_key=self.route_key)
        cached = self.state.get_cached(key)
        if cached is not None:
            return cached
        result = self.provider.analyze(text)
        self.state.set_cached(key, result, self.settings.remote_cache_ttl_seconds)
        raw = dict(result.raw_result)
        raw["web_cache_hit"] = False
        raw["web_cache_key"] = key
        return result.model_copy(update={"raw_result": raw})


class JobRunner:
    def __init__(self, *, settings: WebSettings | None = None, max_workers: int | None = None) -> None:
        self.settings = settings or WebSettings.from_env()
        if max_workers is not None:
            self.settings = self.settings.model_copy(update={"workers": max(1, min(4, max_workers))})
        self.executor = ThreadPoolExecutor(max_workers=self.settings.workers)
        self.jobs: dict[str, JobRecord] = {}
        self.lock = threading.Lock()
        self.remote_state = RemoteEndpointState()

    def submit(self, kind: JobKind, request: DetectRequest | RefineRequest, *, client_id: str = "anonymous") -> JobRecord:
        self.validate_text(request.text)
        decision = self.remote_state.evaluate_and_reserve(
            settings=self.settings,
            request=request,
            client_id=client_id,
            fast_configured=fast_detectgpt_configured(),
        )
        request_to_run = force_local_request(request) if decision.fallback_to_local else request
        context = WebRunContext(
            client_id=client_id,
            remote_decision=decision,
            remote_state=self.remote_state,
            settings=self.settings,
        )
        job = JobRecord(
            job_id=uuid.uuid4().hex[:12],
            kind=kind,
            status="queued",
            request=request_to_run,
            context=context,
        )
        with self.lock:
            self.jobs[job.job_id] = job
        if self.settings.inline_jobs:
            self._run_job(job.job_id, request_to_run)
        else:
            job.future = self.executor.submit(self._run_job, job.job_id, request_to_run)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self.lock:
            return self.jobs.get(job_id)

    def validate_text(self, text: str) -> None:
        if not text.strip():
            raise ValueError("Text is empty.")
        word_count = len(text.split())
        if word_count > self.settings.max_words:
            raise ValueError(f"Text is too long: {word_count} words. Limit is {self.settings.max_words} words.")

    def _run_job(self, job_id: str, request: DetectRequest | RefineRequest) -> None:
        self._set_status(job_id, "running")
        try:
            job = self.get(job_id)
            context = job.context if job is not None else WebRunContext()
            if isinstance(request, RefineRequest):
                result = run_refinement(request, context=context)
            else:
                result = run_detection(request, context=context)
            self._finish(job_id, result=result)
        except Exception as error:  # noqa: BLE001 - web jobs must report failures as job state.
            self._finish(job_id, error=str(error))

    def _set_status(self, job_id: str, status: JobStatus) -> None:
        with self.lock:
            self.jobs[job_id].status = status

    def _finish(self, job_id: str, *, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.finished_at = datetime.now(timezone.utc)
            job.result = result
            job.error = error
            job.status = "failed" if error else "succeeded"
            context = job.context
        if context.remote_decision.reserved:
            context.remote_state.release_remote_job() if context.remote_state is not None else None


def engine_config_for_request(request: DetectRequest | RefineRequest) -> EngineConfig:
    mock_provider = request.mock_provider if isinstance(request, RefineRequest) else None
    cycles = request.cycles if isinstance(request, RefineRequest) else 1
    detector_set = normalize_web_detector_set(request.detectors)
    config = EngineConfig.from_env(
        use_mock_provider=mock_provider,
        max_refinement_cycles=cycles,
        detector_set=detector_set,
    )
    return replace(
        config,
        detector_execution_mode=request.detector_execution,
        detector_concurrency=2 if request.detector_execution == "parallel" else 1,
    )


def remote_requested(detectors: str) -> bool:
    return detectors in {"local+fast-detectgpt", "local+official", "official-fast-detectgpt"}


def force_local_request(request: DetectRequest | RefineRequest) -> DetectRequest | RefineRequest:
    return request.model_copy(update={"detectors": "local"})


def fast_detectgpt_configured() -> bool:
    config = EngineConfig.from_env()
    return bool(config.official_fast_detectgpt_cli or (config.official_flash_endpoint_id and config.runpod_api_key))


def remote_cache_key(*, text: str, provider_name: str, route_key: str) -> str:
    normalized_text = " ".join(text.split())
    digest = hashlib.sha256(f"{provider_name}\n{route_key}\n{normalized_text}".encode("utf-8")).hexdigest()
    return digest


def remote_route_key(config: EngineConfig) -> str:
    if config.official_flash_endpoint_id:
        return f"runpod:{config.official_flash_endpoint_id}:fast-detectgpt"
    if config.official_fast_detectgpt_cli:
        return f"cli:{hashlib.sha256(config.official_fast_detectgpt_cli.encode('utf-8')).hexdigest()[:12]}"
    return "unconfigured"


def normalize_web_detector_set(detectors: str) -> str:
    if detectors in {"local+fast-detectgpt", "local+official"}:
        return "local"
    return detectors


def web_detector_providers(config: EngineConfig, preset: str, context: WebRunContext | None = None):
    if preset in {"local+fast-detectgpt", "local+official"}:
        local_providers = detector_providers_from_config(config)
        fast_config = replace(config, detector_set="official-fast-detectgpt")
        remote_providers = detector_providers_from_config(fast_config)
        return local_providers + wrap_remote_providers(remote_providers, fast_config, context)
    if preset == "official-fast-detectgpt":
        providers = detector_providers_from_config(config)
        return wrap_remote_providers(providers, config, context)
    return None


def wrap_remote_providers(providers, config: EngineConfig, context: WebRunContext | None):
    if context is None or context.remote_state is None or context.settings is None:
        return providers
    if not context.remote_decision.allowed:
        return providers
    route_key = remote_route_key(config)
    wrapped = []
    for provider in providers:
        if getattr(provider, "provider_name", "") == "official_fast_detectgpt":
            wrapped.append(
                CachedRemoteDetectorProvider(
                    provider=provider,
                    state=context.remote_state,
                    settings=context.settings,
                    route_key=route_key,
                )
            )
        else:
            wrapped.append(provider)
    return wrapped


def web_pipeline_for_request(
    request: DetectRequest | RefineRequest,
    context: WebRunContext | None = None,
) -> AcademicRewritePipeline:
    config = engine_config_for_request(request)
    providers = web_detector_providers(config, request.detectors, context)
    return AcademicRewritePipeline(config=config, detector_providers=providers)


def run_detection(request: DetectRequest, context: WebRunContext | None = None) -> dict[str, Any]:
    context = context or WebRunContext()
    pipeline = web_pipeline_for_request(request, context)
    config = pipeline.config
    detectors = pipeline.detector_results(request.text)
    payload = summarize_detector_result(request.text, detectors)
    payload["warnings"] = dedupe_strings(context.policy_warnings + payload.get("warnings", []))
    return {
        "kind": "detect",
        "detector_set": config.detector_set,
        "requested_detector_preset": request.detectors,
        "remote_policy": remote_policy_payload(context),
        **payload,
    }


def run_refinement(request: RefineRequest, context: WebRunContext | None = None) -> dict[str, Any]:
    context = context or WebRunContext()
    before = run_detection(DetectRequest(
        text=request.text,
        detectors=request.detectors,
        detector_execution=request.detector_execution,
    ), context=context)
    pipeline = web_pipeline_for_request(request, context)
    config = pipeline.config
    result = pipeline.run_text(request.text, write_artifact=False)
    report = result.final_report
    selected = report.academic_quality_analysis["selected_candidate"]
    after = report.detector_signal_analysis
    preservation = report.semantic_preservation_analysis
    return {
        "kind": "refine",
        "run_id": result.run_id,
        "detector_set": config.detector_set,
        "requested_detector_preset": request.detectors,
        "remote_policy": remote_policy_payload(context),
        "original_text": request.text,
        "refined_text": report.refined_text,
        "summary": {
            "risk": after["detector_risk_score"],
            "consensus": after["label_consensus"],
            "disagreement": after["disagreement"],
            "before_risk": before["summary"]["risk"],
            "after_risk": after["detector_risk_score"],
            "risk_delta": round(before["summary"]["risk"] - after["detector_risk_score"], 4),
            "after_consensus": after["label_consensus"],
            "selected_source": selected["source"],
            "stop_reason": report.academic_quality_analysis["stop_reason"],
            "weighted_quality": selected["weighted_quality"],
            "utility": selected["utility"],
        },
        "before": before,
        "after": {
            "summary": {
                "risk": after["detector_risk_score"],
                "consensus": after["label_consensus"],
                "disagreement": after["disagreement"],
            },
            "detectors": [summarize_detector(detector) for detector in report.optional_detector_audit],
            "warnings": after["notes"],
        },
        "diagnostic_refinement": report.academic_quality_analysis["diagnostic_refinement"],
        "preservation": preservation,
        "major_revisions": report.major_revisions,
        "warnings": dedupe_strings(context.policy_warnings + list(report.warnings)),
        "artifact_path": result.artifact_path,
        "caveat": report.detector_signal_analysis["caveat"],
    }


def remote_policy_payload(context: WebRunContext) -> dict[str, Any]:
    decision = context.remote_decision
    return {
        "requested": decision.requested,
        "allowed": decision.allowed,
        "fallback_to_local": decision.fallback_to_local,
        "reserved": decision.reserved,
        "warnings": list(decision.warnings),
    }


def summarize_detector(detector) -> dict[str, Any]:
    return {
        "provider_name": detector.provider_name,
        "provider_kind": str(detector.provider_kind),
        "available": detector.available,
        "label": detector.label,
        "score": detector.score,
        "confidence": detector.confidence,
        "error": detector.error,
        "checked_at": detector.checked_at.isoformat(),
    }


def summarize_detector_result(text: str, detectors) -> dict[str, Any]:
    risk, consensus, disagreement, notes = detector_consensus(detectors)
    score = score_candidate(
        original_text=text,
        revised_text=text,
        semantic=SemanticRepresentation(),
        detector_results=detectors,
        risk_flags=[],
    )
    unavailable = [detector.provider_name for detector in detectors if not detector.available]
    warnings = dedupe_strings(list(notes) + list(score.false_positive_risk_notes))
    if unavailable:
        warnings.append(f"Unavailable detectors: {', '.join(unavailable)}.")
    return {
        "summary": {
            "risk": risk,
            "consensus": consensus,
            "disagreement": disagreement,
            "word_count": len(text.split()),
            "available_count": len([detector for detector in detectors if detector.available]),
            "unavailable_count": len(unavailable),
        },
        "style": score.naturalness_diagnostics,
        "warnings": warnings,
        "detectors": [summarize_detector(detector) for detector in detectors],
        "caveat": "Detector-risk signals are diagnostics and do not guarantee any detection outcome.",
    }


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def summarize_refinement_result(result) -> dict[str, Any]:
    report = result.final_report
    after = report.detector_signal_analysis
    quality = report.academic_quality_analysis
    before_item = result.ranked_candidates[0] if result.ranked_candidates else None
    before = None
    if before_item is not None:
        before = {
            "candidate_id": before_item.candidate.candidate_id,
            "summary": {
                "risk": before_item.score_card.detector_risk_score,
                "consensus": before_item.score_card.detector_label_consensus,
                "disagreement": before_item.score_card.detector_disagreement,
                "quality": before_item.score_card.weighted_quality,
                "utility": before_item.score_card.candidate_utility,
            },
            "detectors": [summarize_detector(detector) for detector in before_item.detector_results],
        }
    after_detectors = list(getattr(report, "optional_detector_audit", []) or [])
    if not after_detectors and before_item is not None:
        after_detectors = list(before_item.detector_results)
    return {
        "original_text": result.normalized_input.original_text,
        "refined_text": report.refined_text,
        "summary": {
            "run_id": result.run_id,
            "selected_candidate": quality.get("selected_candidate"),
            "stop_reason": quality.get("stop_reason"),
            "risk": after.get("detector_risk_score"),
            "consensus": after.get("label_consensus"),
            "disagreement": after.get("disagreement"),
            "warnings": report.warnings,
            "caveat": after.get("caveat"),
        },
        "before": before,
        "after": {
            "summary": {
                "risk": after.get("detector_risk_score"),
                "consensus": after.get("label_consensus"),
                "disagreement": after.get("disagreement"),
            },
            "detectors": [summarize_detector(detector) for detector in after_detectors],
            "warnings": after.get("notes", []),
        },
        "diagnostic_refinement": quality.get("diagnostic_refinement", []),
        "preservation": report.semantic_preservation_analysis,
        "artifact_path": result.artifact_path,
    }


def create_app(runner: JobRunner | None = None):
    if FastAPI is None:
        raise RuntimeError("Web dependencies are not installed. Install project runtime dependencies.")
    job_runner = runner or JobRunner()
    app = FastAPI(title="AI Humaniser Academic Engine", version="0.1.0")
    if StaticFiles is not None and STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health() -> dict[str, Any]:
        config = EngineConfig.from_env()
        fast_configured = bool(config.official_fast_detectgpt_cli or (config.official_flash_endpoint_id and config.runpod_api_key))
        return {
            "status": "ok",
            "max_words": job_runner.settings.max_words,
            "workers": job_runner.settings.workers,
            "inline_jobs": job_runner.settings.inline_jobs,
            "detector_presets": ["local", "local+fast-detectgpt", "official-fast-detectgpt"],
            "official_fast_detectgpt": {
                "configured": fast_configured,
                "route": "runpod_flash" if config.official_flash_endpoint_id else "cli" if config.official_fast_detectgpt_cli else None,
                "timeout_seconds": config.official_flash_timeout_seconds
                if config.official_flash_endpoint_id
                else config.official_detector_timeout_seconds,
            },
            "remote_policy": job_runner.remote_state.public(job_runner.settings),
            "refinement_provider": {
                "configured": bool(config.deepseek_api_key),
                "model": config.deepseek_model,
                "mock_default": config.use_mock_provider,
            },
        }

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return index_path.read_text(encoding="utf-8")
        return HTML_PAGE

    @app.post("/api/detect")
    def detect(request: DetectRequest, http_request: Request) -> dict[str, Any]:
        try:
            job = job_runner.submit("detect", request, client_id=client_id_from_request(http_request))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return job.public() if job_runner.settings.inline_jobs else {"job_id": job.job_id, "status": job.status}

    @app.post("/api/refine")
    def refine(request: RefineRequest, http_request: Request) -> dict[str, Any]:
        try:
            job = job_runner.submit("refine", request, client_id=client_id_from_request(http_request))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return job.public() if job_runner.settings.inline_jobs else {"job_id": job.job_id, "status": job.status}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = job_runner.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job.public()

    return app


def client_id_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "anonymous"
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Academic Engine Prototype</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f7f7f4; color: #202124; }
    main { max-width: 1120px; margin: 0 auto; padding: 28px; }
    header { display: flex; justify-content: space-between; gap: 20px; align-items: end; margin-bottom: 22px; }
    h1 { font-size: 28px; margin: 0 0 6px; letter-spacing: 0; }
    p { margin: 0; color: #5a5f65; line-height: 1.45; }
    .tabs { display: flex; gap: 8px; margin: 20px 0 14px; }
    button, select { font: inherit; }
    .tab, .action { border: 1px solid #b7bab7; background: #fff; color: #202124; border-radius: 6px; padding: 9px 12px; cursor: pointer; }
    .tab.active, .action { background: #1f3a3d; border-color: #1f3a3d; color: #fff; }
    .grid { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 18px; align-items: start; }
    section, aside { background: #fff; border: 1px solid #dddeda; border-radius: 8px; padding: 16px; }
    textarea { width: 100%; min-height: 340px; resize: vertical; box-sizing: border-box; border: 1px solid #c7cac5; border-radius: 6px; padding: 12px; font: 15px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    label { display: block; font-size: 13px; color: #4f565b; margin: 0 0 6px; }
    select { width: 100%; border: 1px solid #c7cac5; border-radius: 6px; padding: 9px 10px; background: #fff; margin-bottom: 12px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .action { width: 100%; margin-top: 8px; }
    .status { font-size: 13px; color: #586069; margin-top: 10px; min-height: 20px; }
    pre { white-space: pre-wrap; word-break: break-word; background: #f2f3ef; border-radius: 6px; padding: 12px; max-height: 520px; overflow: auto; font-size: 13px; }
    .metric { display: grid; grid-template-columns: 1fr auto; gap: 12px; padding: 8px 0; border-bottom: 1px solid #eceee9; }
    .metric:last-child { border-bottom: 0; }
    .muted { color: #697076; font-size: 13px; margin-top: 12px; }
    @media (max-width: 860px) { main { padding: 18px; } header, .grid { display: block; } aside { margin-top: 14px; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Academic Engine Prototype</h1>
        <p>Detector diagnostics and bounded refinement for academic text.</p>
      </div>
    </header>
    <div class="tabs">
      <button class="tab active" data-mode="detect">Detector</button>
      <button class="tab" data-mode="refine">Refine</button>
    </div>
    <div class="grid">
      <section>
        <label for="text">Text</label>
        <textarea id="text" placeholder="Paste academic text here"></textarea>
        <div class="status" id="status"></div>
      </section>
      <aside>
        <label for="detectors">Detector preset</label>
        <select id="detectors">
          <option value="local">Local</option>
          <option value="local+official">Local + official</option>
          <option value="official-fast-detectgpt">Fast-DetectGPT only</option>
        </select>
        <div class="row">
          <div>
            <label for="execution">Execution</label>
            <select id="execution">
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
            </select>
          </div>
          <div>
            <label for="cycles">Cycles</label>
            <select id="cycles">
              <option value="1">1</option>
              <option value="2">2</option>
            </select>
          </div>
        </div>
        <button class="action" id="submit">Run detector</button>
        <p class="muted">Scores are diagnostic signals. They are not guarantees about external detector outcomes.</p>
      </aside>
    </div>
    <section style="margin-top:18px">
      <div id="metrics"></div>
      <pre id="result">No result yet.</pre>
    </section>
  </main>
  <script>
    let mode = "detect";
    const tabs = document.querySelectorAll(".tab");
    const submit = document.getElementById("submit");
    const statusEl = document.getElementById("status");
    const resultEl = document.getElementById("result");
    const metricsEl = document.getElementById("metrics");
    tabs.forEach(tab => tab.addEventListener("click", () => {
      tabs.forEach(item => item.classList.remove("active"));
      tab.classList.add("active");
      mode = tab.dataset.mode;
      submit.textContent = mode === "detect" ? "Run detector" : "Refine text";
    }));
    submit.addEventListener("click", async () => {
      const text = document.getElementById("text").value;
      const payload = {
        text,
        detectors: document.getElementById("detectors").value,
        detector_execution: document.getElementById("execution").value
      };
      if (mode === "refine") payload.cycles = Number(document.getElementById("cycles").value);
      statusEl.textContent = "Submitting job...";
      resultEl.textContent = "";
      metricsEl.innerHTML = "";
      const response = await fetch(mode === "detect" ? "/api/detect" : "/api/refine", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const error = await response.json();
        statusEl.textContent = error.detail || "Request failed.";
        return;
      }
      const job = await response.json();
      poll(job.job_id);
    });
    async function poll(jobId) {
      const response = await fetch(`/api/jobs/${jobId}`);
      const job = await response.json();
      statusEl.textContent = `Job ${job.job_id}: ${job.status}`;
      if (job.status === "queued" || job.status === "running") {
        setTimeout(() => poll(jobId), 1200);
        return;
      }
      if (job.status === "failed") {
        resultEl.textContent = job.error || "Job failed.";
        return;
      }
      renderResult(job.result);
    }
    function renderResult(result) {
      const summary = result.summary || {};
      const items = Object.entries(summary).map(([key, value]) => `<div class="metric"><span>${key}</span><strong>${value}</strong></div>`);
      metricsEl.innerHTML = items.join("");
      if (result.refined_text) {
        resultEl.textContent = result.refined_text + "\\n\\n--- report ---\\n" + JSON.stringify(result, null, 2);
      } else {
        resultEl.textContent = JSON.stringify(result, null, 2);
      }
    }
  </script>
</body>
</html>
"""


app = create_app() if FastAPI is not None else None


def main() -> int:
    if FastAPI is None:
        print("Web dependencies are not installed. Install project runtime dependencies.")
        return 2
    import uvicorn

    host = os.getenv("ACADEMIC_ENGINE_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("ACADEMIC_ENGINE_WEB_PORT", "8000"))
    uvicorn.run("academic_engine.web.app:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
