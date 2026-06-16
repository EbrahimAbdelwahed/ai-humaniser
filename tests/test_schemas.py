from academic_engine.schemas import (
    CandidateRevision,
    DetectorBatchRequest,
    DetectorBatchResponse,
    DetectorBatchText,
    DetectorPartialFailure,
    DetectorResult,
    FailureMode,
    ProviderKind,
    Strategy,
)
from academic_engine.config import EngineConfig


def test_schema_validation_accepts_detector_result():
    result = DetectorResult(
        provider_name="local",
        provider_kind=ProviderKind.heuristic,
        label="moderate_risk",
        score=0.4,
        confidence=0.7,
        input_hash="abc",
    )

    assert result.provider_kind == ProviderKind.heuristic


def test_candidate_strategy_is_validated():
    candidate = CandidateRevision(
        candidate_id="c1",
        rewritten_text="Smith (2021) remains unchanged.",
        strategy=Strategy.conservative_academic,
    )

    assert candidate.strategy == Strategy.conservative_academic


def test_config_loads_deepseek_values_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DEEPSEEK_API_KEY=test-key\nDEEPSEEK_BASE_URL=https://example.test\nDEEPSEEK_MODEL=deepseek-v4-flash\n",
        encoding="utf-8",
    )

    config = EngineConfig.from_env(env_file=env_file)

    assert config.deepseek_api_key == "test-key"
    assert config.deepseek_base_url == "https://example.test"
    assert config.use_mock_provider is False


def test_batch_detector_schema_serializes_partial_failure():
    request = DetectorBatchRequest(
        request_id="req-1",
        profile="stable",
        texts=[DetectorBatchText(id="candidate-1", candidate_id="candidate-1", text="Smith (2021) found 12%.")],
        detectors=["roberta_cluster"],
    )
    response = DetectorBatchResponse(
        request_id=request.request_id,
        profile=request.profile,
        errors=[
            DetectorPartialFailure(
                scope="detector",
                detector="radar",
                item_id="candidate-1",
                failure_mode=FailureMode.detector_unavailable,
                message="offline",
            )
        ],
    )

    payload = response.model_dump(mode="json")

    assert payload["errors"][0]["failure_mode"] == "detector_unavailable"
    assert request.model_dump(mode="json")["texts"][0]["candidate_id"] == "candidate-1"
