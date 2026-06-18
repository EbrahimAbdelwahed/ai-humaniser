from __future__ import annotations

import math
import asyncio
import json
import os
import shlex
import subprocess
import sys
import statistics
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from academic_engine.schemas import DetectorResult, ProviderKind
from academic_engine.utils import clamp, sentence_split, stable_hash, word_tokens


class DetectorProvider(ABC):
    provider_name: str

    @abstractmethod
    def analyze(self, text: str) -> DetectorResult:
        raise NotImplementedError


def risk_label(score: float) -> str:
    if score >= 0.62:
        return "elevated_risk"
    if score >= 0.38:
        return "moderate_risk"
    return "lower_risk"


def detector_result(
    *,
    provider_name: str,
    score: float,
    confidence: float,
    raw_result: dict,
    text: str,
    provider_kind: ProviderKind = ProviderKind.heuristic,
    label: str | None = None,
) -> DetectorResult:
    score = round(clamp(score), 4)
    return DetectorResult(
        provider_name=provider_name,
        provider_kind=provider_kind,
        label=label or risk_label(score),
        score=score,
        confidence=round(clamp(confidence), 4),
        raw_result=raw_result,
        input_hash=stable_hash(text),
    )


class StylometryBurstinessDetectorProvider(DetectorProvider):
    provider_name = "local_stylometry_burstiness"

    def analyze(self, text: str) -> DetectorResult:
        sentences = sentence_split(text)
        words = word_tokens(text)
        lengths = [len(word_tokens(sentence)) for sentence in sentences] or [0]
        avg_sentence_len = len(words) / max(1, len(sentences))
        variance = statistics.pvariance(lengths) if len(lengths) > 1 else 0.0
        mean = statistics.mean(lengths) if lengths else 0.0
        coefficient_variation = (math.sqrt(variance) / mean) if mean else 0.0
        uniformity_risk = clamp(1.0 - coefficient_variation / 0.65)
        long_sentence_risk = clamp((avg_sentence_len - 24.0) / 18.0)
        score = 0.18 + 0.48 * uniformity_risk + 0.34 * long_sentence_risk
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.66,
            raw_result={
                "avg_sentence_len": round(avg_sentence_len, 2),
                "sentence_length_variance": round(variance, 4),
                "coefficient_variation": round(coefficient_variation, 4),
                "uniformity_risk": round(uniformity_risk, 4),
                "long_sentence_risk": round(long_sentence_risk, 4),
            },
            text=text,
        )


class LexicalDiversityDetectorProvider(DetectorProvider):
    provider_name = "local_lexical_diversity"

    def analyze(self, text: str) -> DetectorResult:
        words = [word.lower() for word in word_tokens(text)]
        unique_ratio = len(set(words)) / max(1, len(words))
        long_words = [word for word in words if len(word) >= 8]
        long_word_ratio = len(long_words) / max(1, len(words))
        diversity_risk = clamp((0.58 - unique_ratio) / 0.25)
        flat_vocabulary_risk = clamp((0.18 - long_word_ratio) / 0.18)
        score = 0.16 + 0.62 * diversity_risk + 0.22 * flat_vocabulary_risk
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.64,
            raw_result={
                "lexical_diversity": round(unique_ratio, 4),
                "long_word_ratio": round(long_word_ratio, 4),
                "diversity_risk": round(diversity_risk, 4),
                "flat_vocabulary_risk": round(flat_vocabulary_risk, 4),
            },
            text=text,
        )


class GltrLiteProbabilityShapeDetectorProvider(DetectorProvider):
    provider_name = "local_gltr_lite_probability_shape"

    COMMON_WORDS = {
        "the",
        "of",
        "and",
        "to",
        "in",
        "a",
        "that",
        "is",
        "for",
        "on",
        "with",
        "as",
        "by",
        "this",
        "it",
        "from",
        "are",
        "an",
        "be",
        "or",
        "which",
        "can",
        "has",
        "have",
        "was",
        "were",
    }

    def analyze(self, text: str) -> DetectorResult:
        words = [word.lower() for word in word_tokens(text)]
        if not words:
            common_ratio = 0.0
            rare_ratio = 0.0
            transition_repetition = 0.0
        else:
            common_ratio = sum(1 for word in words if word in self.COMMON_WORDS) / len(words)
            rare_ratio = sum(1 for word in words if len(word) >= 11 or "-" in word) / len(words)
            transitions = sum(1 for word in words if word in {"therefore", "furthermore", "moreover", "however", "overall"})
            transition_repetition = transitions / max(1, len(sentence_split(text)))
        predictable_token_risk = clamp((common_ratio - 0.39) / 0.22)
        low_surprisal_risk = clamp((0.075 - rare_ratio) / 0.075)
        transition_risk = clamp(transition_repetition / 0.75)
        score = 0.14 + 0.50 * predictable_token_risk + 0.30 * low_surprisal_risk + 0.06 * transition_risk
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.58,
            raw_result={
                "common_token_ratio": round(common_ratio, 4),
                "rare_token_ratio": round(rare_ratio, 4),
                "transition_repetition": round(transition_repetition, 4),
                "predictable_token_risk": round(predictable_token_risk, 4),
                "low_surprisal_risk": round(low_surprisal_risk, 4),
            },
            text=text,
        )


class RepetitionGenericityDetectorProvider(DetectorProvider):
    provider_name = "local_repetition_genericity"

    GENERIC_MARKERS = [
        "it is important to note",
        "in conclusion",
        "overall,",
        "furthermore",
        "moreover",
        "as a result",
        "this essay",
        "plays a crucial role",
        "significant impact",
    ]

    def analyze(self, text: str) -> DetectorResult:
        sentences = sentence_split(text)
        words = [word.lower() for word in word_tokens(text)]
        lower = text.lower()
        generic_markers = sum(lower.count(marker) for marker in self.GENERIC_MARKERS)
        repeated_openings = len(sentences) - len({sentence.split(" ", 1)[0].lower() for sentence in sentences if sentence})
        repeated_words = sum(1 for word in set(words) if words.count(word) >= 4 and len(word) > 3)
        score = 0.12 + min(0.34, generic_markers * 0.075) + min(0.24, repeated_openings * 0.055) + min(0.28, repeated_words * 0.035)
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.70,
            raw_result={
                "generic_marker_count": generic_markers,
                "repeated_opening_count": repeated_openings,
                "repeated_content_word_count": repeated_words,
            },
            text=text,
        )


class ReadabilityAcademicPatternDetectorProvider(DetectorProvider):
    provider_name = "local_readability_academic_pattern"

    def analyze(self, text: str) -> DetectorResult:
        sentences = sentence_split(text)
        words = word_tokens(text)
        avg_sentence_len = len(words) / max(1, len(sentences))
        avg_word_len = sum(len(word) for word in words) / max(1, len(words))
        hedge_count = sum(text.lower().count(marker) for marker in ["may", "might", "suggests", "indicates", "appears"])
        citation_density = (text.count("(") + text.count(" et al")) / max(1, len(words) / 100)
        over_smooth_risk = clamp((avg_sentence_len - 20.0) / 20.0)
        low_academic_texture_risk = clamp((0.8 - citation_density) / 0.8) * clamp((1.35 - hedge_count / max(1, len(sentences))) / 1.35)
        word_shape_risk = clamp((avg_word_len - 4.6) / 3.0)
        score = 0.18 + 0.38 * over_smooth_risk + 0.34 * low_academic_texture_risk + 0.10 * word_shape_risk
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.61,
            raw_result={
                "avg_sentence_len": round(avg_sentence_len, 2),
                "avg_word_len": round(avg_word_len, 2),
                "hedge_count": hedge_count,
                "citation_density_per_100_words": round(citation_density, 4),
                "over_smooth_risk": round(over_smooth_risk, 4),
                "low_academic_texture_risk": round(low_academic_texture_risk, 4),
            },
            text=text,
        )


class HeuristicDetectorProvider(DetectorProvider):
    provider_name = "local_heuristic_detector_risk"

    def analyze(self, text: str) -> DetectorResult:
        ensemble = lightweight_local_detector_providers(include_legacy=False)
        results = [provider.analyze(text) for provider in ensemble]
        scores = [result.score for result in results if result.available]
        score = sum(scores) / max(1, len(scores))
        return detector_result(
            provider_name=self.provider_name,
            score=score,
            confidence=0.68,
            raw_result={
                "component_scores": {result.provider_name: result.score for result in results},
                "component_labels": {result.provider_name: result.label for result in results},
            },
            text=text,
        )


class HuggingFaceOpenAIDetectorProvider(DetectorProvider):
    provider_name = "hf_roberta_base_openai_detector"

    def __init__(self, model_name: str = "openai-community/roberta-base-openai-detector") -> None:
        self.model_name = model_name

    def analyze(self, text: str) -> DetectorResult:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
        except Exception as error:
            return self.unavailable(text, f"transformers is not installed: {error}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_name, local_files_only=True)
            classifier = pipeline("text-classification", model=model, tokenizer=tokenizer, truncation=True)
            output = classifier(text[:4000])[0]
        except Exception as error:
            return self.unavailable(
                text,
                f"HuggingFace detector model is unavailable locally for {self.model_name!r}: {error}",
            )
        label = str(output.get("label", "unknown")).lower()
        confidence = clamp(float(output.get("score", 0.0)))
        risk_score = confidence if "fake" in label or "ai" in label or "generated" in label else 1.0 - confidence
        return detector_result(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.local_model,
            score=risk_score,
            confidence=confidence,
            label=risk_label(risk_score),
            raw_result={"model_name": self.model_name, "hf_label": output.get("label"), "hf_score": output.get("score")},
            text=text,
        )

    def unavailable(self, text: str, error: str) -> DetectorResult:
        return DetectorResult(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.local_model,
            available=False,
            label="unavailable",
            score=0.0,
            confidence=0.0,
            raw_result={"model_name": self.model_name},
            error=error,
            input_hash=stable_hash(text),
        )


class CommunityDetectorProvider(DetectorProvider):
    provider_kind = ProviderKind.local_model
    install_hint: str

    def unavailable(self, text: str, error: str, raw_result: dict | None = None) -> DetectorResult:
        raw = {"install_hint": self.install_hint}
        if raw_result:
            raw.update(raw_result)
        return DetectorResult(
            provider_name=self.provider_name,
            provider_kind=self.provider_kind,
            available=False,
            label="unavailable",
            score=0.0,
            confidence=0.0,
            raw_result=raw,
            error=error,
            input_hash=stable_hash(text),
        )

    def from_score(self, *, text: str, score: float, confidence: float, raw_result: dict, label: str | None = None) -> DetectorResult:
        return detector_result(
            provider_name=self.provider_name,
            provider_kind=self.provider_kind,
            score=score,
            confidence=confidence,
            raw_result=raw_result,
            text=text,
            label=label,
        )


class BinocularsDetectorProvider(CommunityDetectorProvider):
    provider_name = "community_binoculars"
    install_hint = (
        "Install the official ahans30/Binoculars package/repo and cache the configured models, "
        "or set ACADEMIC_ENGINE_BINOCULARS_CLI to a local command that returns JSON or a numeric AI-risk score."
    )

    def __init__(self, *, model_name: str = "tiiuae/falcon-7b", observer_name: str = "tiiuae/falcon-7b-instruct", cli: str | None = None) -> None:
        self.model_name = model_name
        self.observer_name = observer_name
        self.cli = cli
        self._binoculars = None

    def analyze(self, text: str) -> DetectorResult:
        if self.cli:
            return self._analyze_cli(text, shlex.split(self.cli))
        try:
            from binoculars import Binoculars
        except Exception as error:
            return self.unavailable(text, f"Binoculars import failed: {error}")
        try:
            if self._binoculars is None:
                try:
                    self._binoculars = Binoculars(observer_name_or_path=self.observer_name, performer_name_or_path=self.model_name)
                except TypeError:
                    self._binoculars = Binoculars()
            raw = self._binoculars.compute_score(text)
            score_value = float(raw[0] if isinstance(raw, Sequence) and not isinstance(raw, str) else raw)
            label = "elevated_risk" if score_value < 0.9015310749276843 else "lower_risk"
            risk_score = 1.0 - clamp((score_value - 0.75) / 0.45)
            return self.from_score(
                text=text,
                score=risk_score,
                confidence=0.78,
                label=label,
                raw_result={"binoculars_score": score_value, "model_name": self.model_name, "observer_name": self.observer_name},
            )
        except Exception as error:
            return self.unavailable(text, f"Binoculars analysis failed or models are not cached/loaded: {error}")

    def _analyze_cli(self, text: str, command: list[str]) -> DetectorResult:
        return analyze_with_cli_provider(self, text, command)


class ApiBinocularsDetectorProvider(CommunityDetectorProvider):
    provider_name = "community_binoculars"
    provider_kind = ProviderKind.api
    install_hint = (
        "Configure ACADEMIC_ENGINE_BINOCULARS_OBSERVER_MODEL/BASE_URL/API_KEY and "
        "ACADEMIC_ENGINE_BINOCULARS_PERFORMER_MODEL/BASE_URL/API_KEY against APIs that return token logprobs."
    )

    def __init__(
        self,
        *,
        observer_model: str | None,
        observer_base_url: str | None,
        observer_api_key: str | None,
        performer_model: str | None,
        performer_base_url: str | None,
        performer_api_key: str | None,
        client=None,
    ) -> None:
        self.observer_model = observer_model
        self.observer_base_url = observer_base_url
        self.observer_api_key = observer_api_key
        self.performer_model = performer_model
        self.performer_base_url = performer_base_url
        self.performer_api_key = performer_api_key
        self.client = client

    def analyze(self, text: str) -> DetectorResult:
        missing = [
            name
            for name, value in {
                "observer_model": self.observer_model,
                "observer_base_url": self.observer_base_url,
                "observer_api_key": self.observer_api_key,
                "performer_model": self.performer_model,
                "performer_base_url": self.performer_base_url,
                "performer_api_key": self.performer_api_key,
            }.items()
            if not value
        ]
        if missing:
            return self.unavailable(text, f"Binoculars API cross-perplexity is not configured: missing {', '.join(missing)}.")
        try:
            observer_loss = self._mean_negative_logprob(
                base_url=self.observer_base_url or "",
                api_key=self.observer_api_key or "",
                model=self.observer_model or "",
                text=text,
            )
            performer_loss = self._mean_negative_logprob(
                base_url=self.performer_base_url or "",
                api_key=self.performer_api_key or "",
                model=self.performer_model or "",
                text=text,
            )
        except Exception as error:
            return self.unavailable(text, f"Binoculars API logprobs unavailable or incomplete: {error}")
        binoculars_score = observer_loss / max(performer_loss, 1e-6)
        risk_score = 1.0 - clamp((binoculars_score - 0.90) / 0.35)
        return self.from_score(
            text=text,
            score=risk_score,
            confidence=0.72,
            raw_result={
                "implementation": "api_cross_perplexity_logprobs",
                "observer_model": self.observer_model,
                "performer_model": self.performer_model,
                "binoculars_score": round(binoculars_score, 6),
                "observer_loss": round(observer_loss, 6),
                "performer_loss": round(performer_loss, 6),
            },
        )

    def _mean_negative_logprob(self, *, base_url: str, api_key: str, model: str, text: str) -> float:
        if self.client is not None:
            payload = self.client.logprobs(base_url=base_url, api_key=api_key, model=model, text=text)
        else:
            request = urllib.request.Request(
                base_url.rstrip("/") + "/chat/completions",
                data=json.dumps(
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": text}],
                        "max_tokens": 1,
                        "temperature": 0,
                        "logprobs": True,
                        "top_logprobs": 1,
                    }
                ).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        token_logprobs = payload.get("token_logprobs")
        if token_logprobs is None:
            choices = payload.get("choices") or []
            content = (((choices[0] if choices else {}).get("logprobs") or {}).get("content") or [])
            token_logprobs = [item.get("logprob") for item in content if item.get("logprob") is not None]
        if not token_logprobs:
            raise ValueError("response did not include token logprobs")
        return float(-sum(float(value) for value in token_logprobs) / len(token_logprobs))


class CliCommunityDetectorProvider(CommunityDetectorProvider):
    def __init__(self, *, provider_name: str, cli: str | None, install_hint: str) -> None:
        self.provider_name = provider_name
        self.cli = cli
        self.install_hint = install_hint

    def analyze(self, text: str) -> DetectorResult:
        if not self.cli:
            return self.unavailable(text, "No local CLI/API command is configured for this community detector.")
        return analyze_with_cli_provider(self, text, shlex.split(self.cli))


class OfficialDetectorProvider(CommunityDetectorProvider):
    provider_kind = ProviderKind.local_model

    def __init__(self, *, provider_name: str, cli: str | None, install_hint: str, timeout_seconds: int = 300) -> None:
        self.provider_name = provider_name
        self.cli = cli
        self.install_hint = install_hint
        self.timeout_seconds = timeout_seconds

    def analyze(self, text: str) -> DetectorResult:
        if not self.cli:
            return self.unavailable(text, "No official local CLI command is configured for this detector.")
        return analyze_with_cli_provider(self, text, shlex.split(self.cli), timeout_seconds=self.timeout_seconds)


class RunPodOfficialDetectorProvider(CommunityDetectorProvider):
    provider_kind = ProviderKind.api

    def __init__(
        self,
        *,
        provider_name: str,
        endpoint_id: str | None,
        api_key: str | None,
        timeout_seconds: int = 900,
        install_hint: str,
    ) -> None:
        self.provider_name = provider_name
        self.endpoint_id = endpoint_id
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.install_hint = install_hint

    async def _call_endpoint(self, endpoint_cls, text: str) -> dict:
        endpoint = endpoint_cls(id=self.endpoint_id)
        job = await endpoint.runsync(
            {
                "detector": self.provider_name,
                "text": text,
                "timeout_seconds": self.timeout_seconds,
            },
            timeout=self.timeout_seconds,
        )
        if hasattr(job, "output"):
            if not getattr(job, "done", True) and hasattr(job, "wait"):
                job = await job.wait(timeout=self.timeout_seconds)
            if getattr(job, "error", None):
                raise RuntimeError(str(job.error))
            output = job.output
        else:
            output = job
        if not isinstance(output, dict):
            raise ValueError(f"Endpoint returned {type(output).__name__}, expected JSON object.")
        return output

    def analyze(self, text: str) -> DetectorResult:
        if not self.endpoint_id:
            return self.unavailable(text, "No RunPod Flash endpoint id is configured for this official detector.")
        if not self.api_key:
            return self.unavailable(text, "RUNPOD_API_KEY is not configured for RunPod Flash official detector provider.")
        try:
            from runpod_flash import Endpoint
        except Exception as error:
            return self.unavailable(text, f"runpod_flash is not installed or importable: {error}")
        previous_key = os.environ.get("RUNPOD_API_KEY")
        os.environ["RUNPOD_API_KEY"] = self.api_key
        try:
            output = asyncio.run(self._call_endpoint(Endpoint, text))
        except Exception as error:
            return self.unavailable(text, f"RunPod Flash endpoint call failed for {self.provider_name}: {error}")
        finally:
            if previous_key is None:
                os.environ.pop("RUNPOD_API_KEY", None)
            else:
                os.environ["RUNPOD_API_KEY"] = previous_key
        if output.get("available") is False:
            return self.unavailable(
                text,
                str(output.get("error") or output.get("failure_mode") or f"{self.provider_name} unavailable on RunPod Flash endpoint."),
                output,
            )
        try:
            score, confidence, label, raw = parse_cli_detector_output(json.dumps(output))
        except Exception as error:
            return self.unavailable(text, f"RunPod Flash official detector output could not be parsed: {error}", output)
        raw["endpoint_id"] = self.endpoint_id
        raw["detector"] = self.provider_name
        raw["route"] = "runpod_flash_direct"
        return self.from_score(text=text, score=score, confidence=confidence, label=label, raw_result=raw)


class FlashDetectorProvider(CommunityDetectorProvider):
    provider_kind = ProviderKind.api
    supported_detectors = {"binoculars", "ghostbuster", "mage", "radar", "openai_roberta", "chatgpt_roberta"}
    stable_detectors = {"radar", "openai_roberta", "chatgpt_roberta"}
    install_hint = (
        "Install runpod-flash, set RUNPOD_API_KEY, deploy scripts/runpod_flash detectors, and configure "
        "ACADEMIC_ENGINE_FLASH_ENDPOINT_ID or ACADEMIC_ENGINE_FLASH_<DETECTOR>_ENDPOINT_ID."
    )

    def __init__(
        self,
        *,
        detector_name: str,
        api_key: str | None,
        endpoint_id: str | None,
        timeout_seconds: int = 120,
        profile: str = "stable",
    ) -> None:
        normalized = detector_name.strip().lower()
        self.detector_name = normalized
        self.provider_name = f"flash_{normalized}"
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.timeout_seconds = timeout_seconds
        self.profile = profile

    async def _call_endpoint(self, endpoint_class, text: str):
        endpoint = endpoint_class(id=self.endpoint_id)
        payload = {"detector": self.detector_name, "text": text}
        job = await endpoint.runsync(payload, timeout=self.timeout_seconds)
        if hasattr(job, "output"):
            if not getattr(job, "done", True) and hasattr(job, "wait"):
                job = await job.wait(timeout=self.timeout_seconds)
            if getattr(job, "error", None):
                raise RuntimeError(str(job.error))
            return job.output
        return job

    def _result_from_output(self, text: str, output) -> DetectorResult:
        if not isinstance(output, dict):
            return self.unavailable(text, f"RunPod Flash endpoint returned unsupported output type: {type(output).__name__}")
        if output.get("available") is False:
            return self.unavailable(text, str(output.get("error") or f"{self.detector_name} unavailable on Flash endpoint."), output)
        score = output.get("score", output.get("risk_score", output.get("ai_probability", output.get("probability"))))
        if score is None and "label" in output:
            score = 1.0 if str(output["label"]).lower() in {"ai", "machine", "generated", "elevated_risk"} else 0.0
        if score is None:
            return self.unavailable(text, "RunPod Flash detector output did not include a score-like field.", output)
        parsed_score = float(score)
        if parsed_score > 1.0:
            parsed_score = parsed_score / 100.0
        confidence = float(output.get("confidence", output.get("probability", 0.78)))
        label = str(output["label"]) if "label" in output else None
        raw = dict(output)
        raw["endpoint_id"] = self.endpoint_id
        raw["detector"] = self.detector_name
        raw["flash_profile"] = self.profile
        raw["stable_for_pipeline"] = self.detector_name in self.stable_detectors
        return self.from_score(text=text, score=parsed_score, confidence=confidence, label=label, raw_result=raw)

    def analyze(self, text: str) -> DetectorResult:
        if self.detector_name not in self.supported_detectors:
            return self.unavailable(text, f"Unsupported Flash detector name: {self.detector_name!r}")
        if not self.api_key:
            return self.unavailable(text, "RUNPOD_API_KEY is not configured for Flash detector provider.")
        if not self.endpoint_id:
            return self.unavailable(
                text,
                f"No RunPod Flash endpoint id configured for {self.detector_name}. "
                "Set ACADEMIC_ENGINE_FLASH_ENDPOINT_ID or the detector-specific endpoint env var.",
            )
        if len(text.encode("utf-8")) > 9_500_000:
            return self.unavailable(text, "Input exceeds the RunPod Flash 10MB payload limit.")
        try:
            from runpod_flash import Endpoint
        except Exception as error:
            return self.unavailable(text, f"runpod_flash is not installed or importable: {error}")
        previous_key = os.environ.get("RUNPOD_API_KEY")
        os.environ["RUNPOD_API_KEY"] = self.api_key
        try:
            output = asyncio.run(self._call_endpoint(Endpoint, text))
        except Exception as error:
            return self.unavailable(text, f"RunPod Flash endpoint call failed for {self.detector_name}: {error}")
        finally:
            if previous_key is None:
                os.environ.pop("RUNPOD_API_KEY", None)
            else:
                os.environ["RUNPOD_API_KEY"] = previous_key
        return self._result_from_output(text, output)


def parse_cli_detector_output(output: str) -> tuple[float, float, str | None, dict]:
    stripped = output.strip()
    if not stripped:
        raise ValueError("detector command returned no output")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        score = float(stripped.splitlines()[-1].strip())
        return score, 0.70, None, {"stdout": stripped}
    score = payload.get("score", payload.get("risk_score", payload.get("ai_probability", payload.get("probability"))))
    if score is None and "label" in payload:
        score = 1.0 if str(payload["label"]).lower() in {"ai", "machine", "generated", "elevated_risk"} else 0.0
    if score is None:
        raise ValueError("detector JSON did not include score, risk_score, ai_probability, probability, or label")
    confidence = float(payload.get("confidence", payload.get("probability", 0.70)))
    label = str(payload["label"]) if "label" in payload else None
    parsed_score = float(score)
    if parsed_score > 1.0:
        parsed_score = parsed_score / 100.0
    return parsed_score, confidence, label, payload


def analyze_with_cli_provider(provider: CommunityDetectorProvider, text: str, command: list[str], *, timeout_seconds: int = 300) -> DetectorResult:
    try:
        completed = subprocess.run(command, input=text, text=True, capture_output=True, timeout=timeout_seconds, check=False)
    except Exception as error:
        return provider.unavailable(text, f"{provider.provider_name} command failed to start: {error}", {"command": command})
    if completed.returncode != 0:
        raw_stdout = completed.stdout.strip()
        if raw_stdout:
            try:
                payload = json.loads(raw_stdout)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("available") is False:
                error = str(payload.get("error") or payload.get("failure_mode") or f"{provider.provider_name} unavailable.")
                payload["command"] = command
                return provider.unavailable(text, error, payload)
        return provider.unavailable(
            text,
            f"{provider.provider_name} command exited with {completed.returncode}: {completed.stderr.strip()[:500]}",
            {"command": command, "stdout": completed.stdout.strip()[:500]},
        )
    try:
        score, confidence, label, raw = parse_cli_detector_output(completed.stdout)
    except Exception as error:
        return provider.unavailable(text, f"{provider.provider_name} command output could not be parsed: {error}", {"command": command})
    return provider.from_score(text=text, score=score, confidence=confidence, label=label, raw_result=raw)


def community_detector_providers(config) -> list[DetectorProvider]:
    binoculars_api = ApiBinocularsDetectorProvider(
        observer_model=getattr(config, "binoculars_observer_model", None),
        observer_base_url=getattr(config, "binoculars_observer_base_url", None),
        observer_api_key=getattr(config, "binoculars_observer_api_key", None),
        performer_model=getattr(config, "binoculars_performer_model", None),
        performer_base_url=getattr(config, "binoculars_performer_base_url", None),
        performer_api_key=getattr(config, "binoculars_performer_api_key", None),
    )
    return [
        binoculars_api,
        CliCommunityDetectorProvider(
            provider_name="community_ghostbuster",
            cli=getattr(config, "ghostbuster_cli", None),
            install_hint=(
                "Clone/install vivek3141/ghostbuster locally, then set ACADEMIC_ENGINE_GHOSTBUSTER_CLI "
                "to a command that reads text on stdin and prints JSON with score/confidence or a numeric score."
            ),
        ),
        CliCommunityDetectorProvider(
            provider_name="community_mage",
            cli=getattr(config, "mage_cli", None),
            install_hint=(
                "Clone/install yafuly/MAGE locally, download its model assets, then set ACADEMIC_ENGINE_MAGE_CLI "
                "to a stdin-to-JSON/numeric local command."
            ),
        ),
        CliCommunityDetectorProvider(
            provider_name="community_radar",
            cli=getattr(config, "radar_cli", None),
            install_hint=(
                "Install an official IBM/RADAR local model/script, then set ACADEMIC_ENGINE_RADAR_CLI "
                "to a stdin-to-JSON/numeric local command."
            ),
        ),
    ]


def official_detector_providers(config) -> list[DetectorProvider]:
    timeout_seconds = getattr(config, "official_detector_timeout_seconds", 300)
    binoculars_cli = getattr(config, "official_binoculars_cli", None) or _official_flash_cli(config, "official_binoculars")
    official_flash_endpoint_id = getattr(config, "official_flash_endpoint_id", None)
    runpod_api_key = getattr(config, "runpod_api_key", None)
    fast_detectgpt_cli = getattr(config, "official_fast_detectgpt_cli", None)
    if getattr(config, "official_flash_endpoint_id", None):
        timeout_seconds = max(timeout_seconds, int(getattr(config, "official_flash_timeout_seconds", 900)))
    fast_detectgpt_provider: DetectorProvider
    if official_flash_endpoint_id:
        fast_detectgpt_provider = RunPodOfficialDetectorProvider(
            provider_name="official_fast_detectgpt",
            endpoint_id=official_flash_endpoint_id,
            api_key=runpod_api_key,
            timeout_seconds=timeout_seconds,
            install_hint=(
                "Set RUNPOD_API_KEY and ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID for the deployed "
                "official RunPod Flash endpoint."
            ),
        )
    else:
        fast_detectgpt_provider = OfficialDetectorProvider(
            provider_name="official_fast_detectgpt",
            cli=fast_detectgpt_cli,
            timeout_seconds=timeout_seconds,
            install_hint=(
                "Install/cache the official Fast-DetectGPT repository locally, then set "
                "ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI to a stdin-to-JSON/numeric wrapper command, "
                "or deploy the official RunPod Flash endpoint and set ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID."
            ),
        )
    return [
        OfficialDetectorProvider(
            provider_name="official_binoculars",
            cli=binoculars_cli,
            timeout_seconds=timeout_seconds,
            install_hint=(
                "Install/cache the official Binoculars repository locally, then set "
                "ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI to a stdin-to-JSON/numeric wrapper command, "
                "or deploy the official RunPod Flash endpoint and set ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID."
            ),
        ),
        OfficialDetectorProvider(
            provider_name="official_ghostbuster",
            cli=getattr(config, "official_ghostbuster_cli", None),
            timeout_seconds=timeout_seconds,
            install_hint=(
                "Install/cache the official Ghostbuster repository locally, then set "
                "ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI to a stdin-to-JSON/numeric wrapper command."
            ),
        ),
        fast_detectgpt_provider,
    ]


def _official_flash_cli(config, detector: str) -> str | None:
    endpoint_id = getattr(config, "official_flash_endpoint_id", None)
    if not endpoint_id:
        return None
    repo_root = Path(__file__).resolve().parents[2]
    client = repo_root / "scripts" / "official" / "runpod_official_cli.py"
    if not client.exists():
        return None
    timeout = int(getattr(config, "official_flash_timeout_seconds", 900))
    return shlex.join(
        [
            sys.executable,
            str(client),
            "--endpoint-id",
            str(endpoint_id),
            "--detector",
            detector,
            "--timeout",
            str(timeout),
            "--env-file",
            ".env",
        ]
    )


def flash_detector_providers(config) -> list[DetectorProvider]:
    from academic_engine.detector_batch import RunPodBatchDetectorProvider

    endpoint_ids = getattr(config, "flash_endpoint_ids", None) or {}
    shared_endpoint_id = getattr(config, "flash_endpoint_id", None)
    api_key = getattr(config, "runpod_api_key", None)
    timeout_seconds = getattr(config, "flash_timeout_seconds", 120)
    profile = getattr(config, "flash_detector_profile", "stable")
    names = tuple(getattr(config, "flash_detector_names", ("roberta_cluster",)))
    if "roberta_cluster" in names:
        non_cluster = [name for name in names if name not in {"roberta_cluster", "binoculars"}]
        providers: list[DetectorProvider] = [
            RunPodBatchDetectorProvider(
                api_key=api_key,
                endpoint_id=shared_endpoint_id,
                timeout_seconds=timeout_seconds,
                profile=profile,
                detectors=("roberta_cluster",),
            )
        ]
        providers.extend(
            FlashDetectorProvider(
                detector_name=name,
                api_key=api_key,
                endpoint_id=endpoint_ids.get(name) or shared_endpoint_id,
                timeout_seconds=timeout_seconds,
                profile=profile,
            )
            for name in non_cluster
        )
        return providers
    return [
        FlashDetectorProvider(
            detector_name=name,
            api_key=api_key,
            endpoint_id=endpoint_ids.get(name) or shared_endpoint_id,
            timeout_seconds=timeout_seconds,
            profile=profile,
        )
        for name in names
    ]


def lightweight_local_detector_providers(*, include_legacy: bool = True) -> list[DetectorProvider]:
    providers: list[DetectorProvider] = [
        StylometryBurstinessDetectorProvider(),
        LexicalDiversityDetectorProvider(),
        GltrLiteProbabilityShapeDetectorProvider(),
        RepetitionGenericityDetectorProvider(),
        ReadabilityAcademicPatternDetectorProvider(),
    ]
    if include_legacy:
        providers.append(HeuristicDetectorProvider())
    return providers


def detector_providers_from_config(config) -> list[DetectorProvider]:
    detector_set = getattr(config, "detector_set", "local")
    providers: list[DetectorProvider] = []
    if detector_set in {"local", "local+hf", "local+community", "local+flash", "local+official", "community+flash", "all"}:
        providers.extend(lightweight_local_detector_providers())
    if detector_set in {"community", "local+community", "community+flash", "all"}:
        providers.extend(community_detector_providers(config))
    if detector_set in {"official-binoculars"}:
        providers.extend([provider for provider in official_detector_providers(config) if provider.provider_name == "official_binoculars"])
    if detector_set in {"official-fast-detectgpt"}:
        providers.extend([provider for provider in official_detector_providers(config) if provider.provider_name == "official_fast_detectgpt"])
    if detector_set in {"official", "local+official", "all"}:
        providers.extend(official_detector_providers(config))
    if detector_set in {"flash", "local+flash", "community+flash", "all"}:
        providers.extend(flash_detector_providers(config))
    if getattr(config, "include_hf_detector", False) or detector_set in {"hf", "all"}:
        providers.append(HuggingFaceOpenAIDetectorProvider(getattr(config, "hf_detector_model", "openai-community/roberta-base-openai-detector")))
    return providers


class ExternalDetectorProvider(DetectorProvider):
    def __init__(self, provider_name: str, provider_kind: ProviderKind = ProviderKind.api) -> None:
        self.provider_name = provider_name
        self.provider_kind = provider_kind

    def analyze(self, text: str) -> DetectorResult:
        return DetectorResult(
            provider_name=self.provider_name,
            provider_kind=self.provider_kind,
            available=False,
            label="unavailable",
            score=0.0,
            confidence=0.0,
            raw_result={},
            error="External detector adapter is configured but not implemented in Phase 1.",
            input_hash=stable_hash(text),
        )
