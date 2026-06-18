from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient

from academic_engine.detectors import detector_result
from academic_engine.schemas import ProviderKind
from academic_engine.web import app as web_app


def test_vercel_entrypoint_exports_asgi_app():
    from api.index import app

    assert callable(app)
    assert getattr(app, "title", "") == "AI Humaniser Academic Engine"


def _sample_detector(name: str = "local_sample", *, available: bool = True):
    result = detector_result(
        provider_name=name,
        score=0.41,
        confidence=0.8,
        raw_result={"internal": "not exposed"},
        text="Smith (2021) reports a measured 12% change in support.",
        provider_kind=ProviderKind.heuristic,
    )
    result.available = available
    if not available:
        result.error = "missing endpoint config"
    return result


def test_health_endpoint_reports_web_limits(monkeypatch):
    monkeypatch.setenv("ACADEMIC_ENGINE_WEB_MAX_WORDS", "75")
    monkeypatch.setenv("ACADEMIC_ENGINE_REMOTE_MAX_WORDS", "90")
    client = TestClient(web_app.create_app(web_app.JobRunner(max_workers=1)))

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["max_words"] == 75
    assert "local+fast-detectgpt" in payload["detector_presets"]
    assert "official-fast-detectgpt" in payload["detector_presets"]
    assert payload["official_fast_detectgpt"]["configured"] is False
    assert payload["remote_policy"]["max_words"] == 90
    assert payload["remote_policy"]["enabled"] is True
    assert payload["refinement_provider"]["model"]


def test_health_endpoint_reports_fast_detectgpt_runpod_configuration(monkeypatch):
    monkeypatch.setenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID", "endpoint-123")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    client = TestClient(web_app.create_app(web_app.JobRunner(max_workers=1)))

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["official_fast_detectgpt"]["configured"] is True
    assert payload["official_fast_detectgpt"]["route"] == "runpod_flash"


def test_detect_job_submission_and_polling(monkeypatch):
    def fake_detection(request, context=None):
        return {
            "summary": {"risk": 0.41, "consensus": "moderate_risk", "disagreement": 0.0},
            "detectors": [{"provider_name": "local_sample", "available": True}],
            "warnings": [],
            "remote_policy": web_app.remote_policy_payload(context or web_app.WebRunContext()),
        }

    monkeypatch.setattr(web_app, "run_detection", fake_detection)
    client = TestClient(web_app.create_app(web_app.JobRunner(max_workers=1)))

    response = client.post(
        "/api/detect",
        json={
            "text": "Smith (2021) reports a measured 12% change in support.",
            "detectors": "local",
            "detector_execution": "sequential",
        },
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(20):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "succeeded":
            break
        time.sleep(0.02)
    assert job["kind"] == "detect"
    assert job["status"] == "succeeded"
    assert job["result"]["summary"]["risk"] == 0.41


def test_inline_detect_job_returns_completed_payload(monkeypatch):
    def fake_detection(request, context=None):
        return {
            "summary": {"risk": 0.37, "consensus": "lower_risk", "disagreement": 0.0},
            "detectors": [{"provider_name": "local_sample", "available": True}],
            "warnings": [],
            "remote_policy": web_app.remote_policy_payload(context or web_app.WebRunContext()),
        }

    monkeypatch.setattr(web_app, "run_detection", fake_detection)
    settings = web_app.WebSettings(inline_jobs=True)
    client = TestClient(web_app.create_app(web_app.JobRunner(settings=settings, max_workers=1)))

    response = client.post(
        "/api/detect",
        json={
            "text": "Smith (2021) reports a measured 12% change in support.",
            "detectors": "local",
            "detector_execution": "sequential",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["result"]["summary"]["risk"] == 0.37


def test_remote_detector_policy_disabled_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("ACADEMIC_ENGINE_ENABLE_REMOTE_DETECTORS", "false")
    monkeypatch.setenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID", "endpoint-123")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")

    seen = {}

    def fake_detection(request, context=None):
        seen["detectors"] = request.detectors
        return {
            "summary": {"risk": 0.31, "consensus": "lower_risk", "disagreement": 0.0},
            "detectors": [{"provider_name": "local_sample", "available": True}],
            "warnings": list((context or web_app.WebRunContext()).policy_warnings),
            "remote_policy": web_app.remote_policy_payload(context or web_app.WebRunContext()),
        }

    monkeypatch.setattr(web_app, "run_detection", fake_detection)
    client = TestClient(web_app.create_app(web_app.JobRunner(max_workers=1)))

    response = client.post(
        "/api/detect",
        json={
            "text": "Smith (2021) reports a measured 12% change in support.",
            "detectors": "local+fast-detectgpt",
            "detector_execution": "sequential",
        },
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    for _ in range(20):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "succeeded":
            break
        time.sleep(0.02)
    assert seen["detectors"] == "local"
    assert job["result"]["remote_policy"]["requested"] is True
    assert job["result"]["remote_policy"]["fallback_to_local"] is True
    assert "local diagnostic completed" in " ".join(job["result"]["warnings"])


def test_remote_detector_per_client_daily_limit_falls_back(monkeypatch):
    monkeypatch.setenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID", "endpoint-123")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")

    def fake_detection(request, context=None):
        return {
            "requested": request.detectors,
            "summary": {"risk": 0.31, "consensus": "lower_risk", "disagreement": 0.0},
            "detectors": [],
            "warnings": list((context or web_app.WebRunContext()).policy_warnings),
            "remote_policy": web_app.remote_policy_payload(context or web_app.WebRunContext()),
        }

    settings = web_app.WebSettings(
        remote_per_client_daily_limit=1,
        remote_min_interval_seconds=0,
        remote_global_daily_limit=10,
        remote_max_concurrent_jobs=1,
    )
    runner = web_app.JobRunner(settings=settings, max_workers=1)
    monkeypatch.setattr(web_app, "run_detection", fake_detection)

    first = runner.submit(
        "detect",
        web_app.DetectRequest(text="Smith (2021) reports a measured 12% change.", detectors="local+fast-detectgpt"),
        client_id="client-a",
    )
    for _ in range(20):
        first_job = runner.get(first.job_id)
        if first_job and first_job.status == "succeeded":
            break
        time.sleep(0.02)

    second = runner.submit(
        "detect",
        web_app.DetectRequest(text="Smith (2021) reports a measured 12% change.", detectors="local+fast-detectgpt"),
        client_id="client-a",
    )
    for _ in range(20):
        second_job = runner.get(second.job_id)
        if second_job and second_job.status == "succeeded":
            break
        time.sleep(0.02)

    assert first_job.result["remote_policy"]["allowed"] is True
    assert second_job.result["requested"] == "local"
    assert second_job.result["remote_policy"]["fallback_to_local"] is True
    assert "daily limit" in " ".join(second_job.result["warnings"])


def test_cached_remote_detector_provider_reuses_detector_result():
    class CountingProvider:
        provider_name = "official_fast_detectgpt"

        def __init__(self):
            self.calls = 0

        def analyze(self, text):
            self.calls += 1
            return _sample_detector("official_fast_detectgpt")

    state = web_app.RemoteEndpointState()
    settings = web_app.WebSettings(remote_cache_ttl_seconds=60)
    provider = CountingProvider()
    cached = web_app.CachedRemoteDetectorProvider(
        provider=provider,
        state=state,
        settings=settings,
        route_key="runpod:endpoint-123:fast-detectgpt",
    )

    first = cached.analyze("Smith (2021) reports a measured 12% change.")
    second = cached.analyze("Smith (2021) reports a measured 12% change.")

    assert provider.calls == 1
    assert first.raw_result["web_cache_hit"] is False
    assert second.raw_result["web_cache_hit"] is True
    assert second.provider_name == "official_fast_detectgpt"


def test_input_length_validation(monkeypatch):
    monkeypatch.setenv("ACADEMIC_ENGINE_WEB_MAX_WORDS", "50")
    client = TestClient(web_app.create_app(web_app.JobRunner(max_workers=1)))

    response = client.post(
        "/api/detect",
        json={
            "text": " ".join(["word"] * 51),
            "detectors": "local",
            "detector_execution": "sequential",
        },
    )

    assert response.status_code == 400
    assert "Limit is 50 words" in response.json()["detail"]


def test_detector_summary_does_not_expose_raw_or_hash():
    unavailable = _sample_detector("official_fast_detectgpt", available=False)

    payload = web_app.summarize_detector_result("Short academic text.", [unavailable])

    assert payload["summary"]["unavailable_count"] == 1
    assert payload["detectors"][0]["provider_name"] == "official_fast_detectgpt"
    assert payload["detectors"][0]["error"] == "missing endpoint config"
    assert "raw_result" not in payload["detectors"][0]
    assert "input_hash" not in payload["detectors"][0]


def test_local_fast_web_preset_excludes_other_official_detectors(monkeypatch):
    monkeypatch.delenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID", raising=False)

    request = web_app.DetectRequest(
        text="Smith (2021) reports a measured 12% change in support.",
        detectors="local+fast-detectgpt",
    )
    pipeline = web_app.web_pipeline_for_request(request)
    names = [provider.provider_name for provider in pipeline.detectors]

    assert "official_fast_detectgpt" in names
    assert "official_binoculars" not in names
    assert "official_ghostbuster" not in names


def test_detection_payload_reports_requested_web_preset(monkeypatch):
    detector = _sample_detector()

    class FakePipeline:
        config = SimpleNamespace(detector_set="local")

        def detector_results(self, text):
            return [detector]

    monkeypatch.setattr(web_app, "web_pipeline_for_request", lambda request, context=None: FakePipeline())
    request = web_app.DetectRequest(
        text="Smith (2021) reports a measured 12% change in support.",
        detectors="local+fast-detectgpt",
    )

    payload = web_app.run_detection(request)

    assert payload["detector_set"] == "local"
    assert payload["requested_detector_preset"] == "local+fast-detectgpt"


def test_refinement_summary_shape():
    detector = _sample_detector()
    score = SimpleNamespace(
        detector_risk_score=0.41,
        detector_label_consensus="moderate_risk",
        detector_disagreement=0.0,
        weighted_quality=0.82,
        candidate_utility=0.76,
    )
    ranked = SimpleNamespace(
        candidate=SimpleNamespace(candidate_id="candidate-1"),
        score_card=score,
        detector_results=[detector],
    )
    report = SimpleNamespace(
        refined_text="Refined text.",
        warnings=[],
        detector_signal_analysis={
            "detector_risk_score": 0.39,
            "label_consensus": "moderate_risk",
            "disagreement": 0.0,
            "caveat": "Detector-risk signals are heuristics.",
        },
        academic_quality_analysis={
            "selected_candidate": {"candidate_id": "candidate-1"},
            "stop_reason": "initial_candidate_met_quality_and_detector_targets",
            "diagnostic_refinement": [],
        },
        semantic_preservation_analysis={"hard_constraint_failures": []},
    )
    result = SimpleNamespace(
        run_id="run-1",
        normalized_input=SimpleNamespace(original_text="Original text."),
        ranked_candidates=[ranked],
        refinement_cycles=[],
        final_report=report,
        artifact_path=None,
    )

    payload = web_app.summarize_refinement_result(result)

    assert payload["original_text"] == "Original text."
    assert payload["refined_text"] == "Refined text."
    assert payload["before"]["summary"]["risk"] == 0.41
    assert payload["after"]["detectors"][0]["provider_name"] == "local_sample"
    assert payload["artifact_path"] is None
