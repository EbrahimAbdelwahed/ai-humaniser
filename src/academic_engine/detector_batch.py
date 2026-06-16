from __future__ import annotations

import asyncio
import os
import statistics
import uuid
from collections.abc import Sequence

from academic_engine.detector_registry import expand_runtime_detectors
from academic_engine.detectors import CommunityDetectorProvider, risk_label
from academic_engine.schemas import (
    DetectorBatchRequest,
    DetectorBatchResponse,
    DetectorBatchResult,
    DetectorBatchText,
    DetectorPartialFailure,
    DetectorResult,
    DetectorSignal,
    FailureMode,
    ProviderKind,
)
from academic_engine.utils import clamp, stable_hash


class BatchDetectorProvider:
    provider_name: str

    def analyze_batch(self, texts: Sequence[tuple[str, str]]) -> dict[str, list[DetectorResult]]:
        raise NotImplementedError


class RunPodBatchDetectorProvider(CommunityDetectorProvider, BatchDetectorProvider):
    provider_kind = ProviderKind.api
    provider_name = "flash_roberta_cluster"
    install_hint = (
        "Install runpod-flash, set RUNPOD_API_KEY, deploy the offline-safe batch detector endpoint, "
        "and configure ACADEMIC_ENGINE_FLASH_ENDPOINT_ID."
    )

    def __init__(
        self,
        *,
        api_key: str | None,
        endpoint_id: str | None,
        timeout_seconds: int = 120,
        profile: str = "stable",
        detectors: tuple[str, ...] = ("roberta_cluster",),
    ) -> None:
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.timeout_seconds = timeout_seconds
        self.profile = profile
        self.detectors = detectors

    def analyze(self, text: str) -> DetectorResult:
        return self.analyze_batch((("single", text),)).get("single", [self._unavailable_result("single", text, "Batch provider returned no result.")])[0]

    def analyze_batch(self, texts: Sequence[tuple[str, str]]) -> dict[str, list[DetectorResult]]:
        if not texts:
            return {}
        unavailable = self._preflight_unavailable()
        if unavailable:
            return {item_id: [self._unavailable_result(item_id, text, unavailable)] for item_id, text in texts}
        items = [
            DetectorBatchText(id=item_id, candidate_id=item_id, text=text, source="candidate")
            for item_id, text in texts
        ]
        request = DetectorBatchRequest(
            operation="score_batch",
            profile=self.profile,
            detectors=list(self.detectors),
            texts=items,
            request_id=uuid.uuid4().hex,
            return_raw=True,
        )
        try:
            from runpod_flash import Endpoint
        except Exception as error:
            message = f"runpod_flash is not installed or importable: {error}"
            return {item_id: [self._unavailable_result(item_id, text, message)] for item_id, text in texts}
        previous_key = os.environ.get("RUNPOD_API_KEY")
        os.environ["RUNPOD_API_KEY"] = self.api_key or ""
        try:
            output = asyncio.run(self._call_endpoint(Endpoint, request.model_dump(mode="json")))
            response = DetectorBatchResponse.model_validate(output)
        except Exception as error:
            message = f"RunPod Flash batch endpoint call failed: {error}"
            return {item_id: [self._unavailable_result(item_id, text, message)] for item_id, text in texts}
        finally:
            if previous_key is None:
                os.environ.pop("RUNPOD_API_KEY", None)
            else:
                os.environ["RUNPOD_API_KEY"] = previous_key
        text_by_id = dict(texts)
        return {
            result.id: [self._detector_result_from_batch(result, text_by_id.get(result.id, ""))]
            for result in response.results
        }

    async def _call_endpoint(self, endpoint_class, payload: dict):
        endpoint = endpoint_class(id=self.endpoint_id)
        job = await endpoint.runsync(payload, timeout=self.timeout_seconds)
        if hasattr(job, "output"):
            if not getattr(job, "done", True) and hasattr(job, "wait"):
                job = await job.wait(timeout=self.timeout_seconds)
            if getattr(job, "error", None):
                raise RuntimeError(str(job.error))
            return job.output
        return job

    def _preflight_unavailable(self) -> str | None:
        if not self.api_key:
            return "RUNPOD_API_KEY is not configured for Flash batch detector provider."
        if not self.endpoint_id:
            return "No RunPod Flash endpoint id configured. Set ACADEMIC_ENGINE_FLASH_ENDPOINT_ID."
        if not self.detectors:
            return "No detectors configured for Flash batch detector provider."
        return None

    def _detector_result_from_batch(self, result: DetectorBatchResult, text: str) -> DetectorResult:
        cluster = next((cluster for cluster in result.clustered_signals if cluster.cluster == "roberta_cluster"), None)
        score = result.artificiality_risk
        confidence = 0.78
        if cluster is not None:
            score = cluster.score
            available_count = len([member for member in cluster.members if member.available])
            confidence = clamp(0.60 + 0.10 * available_count - 0.25 * cluster.disagreement)
        raw = result.model_dump(mode="json")
        raw["flash_profile"] = self.profile
        raw["runtime_detectors"] = list(expand_runtime_detectors(tuple(self.detectors)))
        return DetectorResult(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.api,
            available=not any(signal.available is False for signal in result.signals) or bool(score),
            label=risk_label(score),
            score=round(clamp(score), 4),
            confidence=round(clamp(confidence), 4),
            raw_result=raw,
            input_hash=stable_hash(text),
        )

    def _unavailable_result(self, item_id: str, text: str, error: str) -> DetectorResult:
        return DetectorResult(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.api,
            available=False,
            label="unavailable",
            score=0.0,
            confidence=0.0,
            raw_result={"candidate_id": item_id, "profile": self.profile, "detectors": list(self.detectors)},
            error=error,
            input_hash=stable_hash(text),
        )


def batch_response_from_member_outputs(
    *,
    request: DetectorBatchRequest,
    member_outputs: dict[str, list[dict]],
    device: str,
    timing: dict | None = None,
) -> DetectorBatchResponse:
    results: list[DetectorBatchResult] = []
    errors: list[DetectorPartialFailure] = []
    for item in request.texts:
        signals: list[DetectorSignal] = []
        for output in member_outputs.get(item.id, []):
            detector = str(output.get("detector", "unknown"))
            available = bool(output.get("available", False))
            if not available:
                errors.append(
                    DetectorPartialFailure(
                        scope="detector",
                        detector=detector,
                        item_id=item.id,
                        failure_mode=FailureMode.detector_unavailable,
                        message=str(output.get("error") or "detector unavailable"),
                    )
                )
            signals.append(
                DetectorSignal(
                    detector=detector,
                    available=available,
                    score=round(clamp(float(output.get("score") or 0.0)), 4),
                    confidence=round(clamp(float(output.get("confidence") or 0.0)), 4),
                    label=str(output.get("label") or ("unavailable" if not available else risk_label(float(output.get("score") or 0.0)))),
                    raw_result=output,
                    error=str(output.get("error")) if output.get("error") else None,
                )
            )
        available_scores = [signal.score for signal in signals if signal.available]
        mean_score = statistics.mean(available_scores) if available_scores else 0.0
        median_score = statistics.median(available_scores) if available_scores else 0.0
        disagreement = max(available_scores) - min(available_scores) if len(available_scores) > 1 else 0.0
        results.append(
            DetectorBatchResult(
                id=item.id,
                candidate_id=item.candidate_id,
                signals=signals,
                clustered_signals=[
                    {
                        "cluster": "roberta_cluster",
                        "members": [signal.model_dump(mode="json") for signal in signals],
                        "score": round(clamp(mean_score), 4),
                        "median_score": round(clamp(median_score), 4),
                        "disagreement": round(clamp(disagreement), 4),
                        "unavailable_members": [signal.detector for signal in signals if not signal.available],
                    }
                ],
                raw_detector_results={signal.detector: signal.raw_result for signal in signals},
                detector_disagreement=round(clamp(disagreement), 4),
                artificiality_risk=round(clamp(mean_score), 4),
                warnings=[f"{signal.detector} unavailable" for signal in signals if not signal.available],
            )
        )
    telemetry = timing or {}
    return DetectorBatchResponse(
        request_id=request.request_id,
        profile=request.profile,
        device=device,
        results=results,
        timing={
            "total_seconds": float(telemetry.get("total_seconds", 0.0)),
            "model_load_seconds": telemetry.get("model_load_seconds", {}),
            "inference_seconds": telemetry.get("inference_seconds", {}),
            "batch_size": len(request.texts),
        },
        loaded_models=list(telemetry.get("loaded_models", [])),
        errors=errors,
    )
