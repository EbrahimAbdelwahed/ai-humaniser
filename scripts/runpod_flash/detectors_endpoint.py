from __future__ import annotations

import statistics
import time

from runpod_flash import Endpoint, GpuGroup


_SEQUENCE_MODEL_CACHE = {}
_CAUSAL_LM_CACHE = {}
_MODEL_LOAD_SECONDS = {}


@Endpoint(
    name="academic-engine-detectors-small-v1",
    gpu=GpuGroup.AMPERE_16,
    workers=(0, 1),
    idle_timeout=45,
    dependencies=[
        "torch",
        "transformers>=4.40",
        "accelerate",
        "sentencepiece",
        "protobuf",
    ],
)
async def detect(data: dict | None = None, **kwargs):
    data = dict(data or {})
    data.update(kwargs)
    operation = str(data.get("operation") or data.get("detector") or "score").lower()
    if operation == "health":
        return _health()
    if operation == "model_inventory":
        return _model_inventory()
    if operation == "score_batch":
        return _score_batch(data)
    detector = str(data.get("detector", "binoculars")).lower()
    text = str(data.get("text", ""))
    if len(text.encode("utf-8")) > 9_500_000:
        return {"available": False, "detector": detector, "error": "Payload exceeds safe 10MB RunPod Flash limit."}
    if detector == "health":
        return _health()
    if not text.strip():
        return {"available": False, "detector": detector, "error": "Empty text cannot be scored."}
    if detector == "binoculars":
        return _binoculars_proxy(data, text)
    if detector == "mage":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="mage",
            default_model="yaful/MAGE",
            default_ai_label_index=1,
        )
    if detector == "openai_roberta":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="openai_roberta",
            default_model="openai-community/roberta-base-openai-detector",
            default_ai_label_index=1,
        )
    if detector == "chatgpt_roberta":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="chatgpt_roberta",
            default_model="Hello-SimpleAI/chatgpt-detector-roberta",
            default_ai_label_index=1,
        )
    if detector == "radar":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="radar",
            default_model="Shushant/adal-roberta-detector",
            default_ai_label_index=0,
        )
    if detector == "ghostbuster":
        return _ghostbuster_feature_proxy(text)
    return {"available": False, "detector": detector, "error": f"Unsupported detector: {detector}"}


def _health():
    return {
        "available": True,
        "operation": "health",
        "implementation": "endpoint_health",
        "profiles": {
            "stable": ["roberta_cluster"],
            "calibration": ["roberta_cluster"],
            "experimental": ["roberta_cluster", "binoculars", "ghostbuster"],
        },
        "clusters": {"roberta_cluster": ["radar", "openai_roberta", "chatgpt_roberta"]},
        "stable_detectors": ["radar", "openai_roberta", "chatgpt_roberta"],
        "experimental_detectors": ["binoculars", "ghostbuster", "mage"],
        "notes": [
            "RoBERTa-like models are returned as one roberta_cluster signal.",
            "Binoculars proxy is legacy experimental only; API-configured logprobs should be used outside this batch endpoint.",
            "No warmup is performed unless explicitly requested by a separate operation.",
        ],
    }


def _model_inventory():
    return {
        "available": True,
        "operation": "model_inventory",
        "device": _device(),
        "loaded_models": [str(key[0]) for key in _SEQUENCE_MODEL_CACHE.keys()],
        "model_load_seconds": dict(_MODEL_LOAD_SECONDS),
        "models": {
            "radar": "Shushant/adal-roberta-detector",
            "openai_roberta": "openai-community/roberta-base-openai-detector",
            "chatgpt_roberta": "Hello-SimpleAI/chatgpt-detector-roberta",
        },
        "clusters": {"roberta_cluster": ["radar", "openai_roberta", "chatgpt_roberta"]},
    }


def _expand_detectors(data: dict) -> list[str]:
    detectors = data.get("detectors") or [data.get("profile") or "stable"]
    expanded = []
    for detector in detectors:
        name = str(detector).lower()
        if name in {"stable", "model", "roberta_cluster"}:
            expanded.extend(["radar", "openai_roberta", "chatgpt_roberta"])
        elif name == "calibration":
            expanded.extend(["radar", "openai_roberta", "chatgpt_roberta"])
        else:
            expanded.append(name)
    return list(dict.fromkeys(expanded))


def _score_batch(data: dict):
    started = time.perf_counter()
    texts = data.get("texts") or []
    request_id = str(data.get("request_id") or "")
    profile = str(data.get("profile") or "stable")
    detectors = _expand_detectors(data)
    results = []
    errors = []
    inference_seconds = {}
    for item in texts:
        item_id = str(item.get("id") or item.get("candidate_id") or len(results))
        text = str(item.get("text") or "")
        signals = []
        raw = {}
        for detector in detectors:
            detector_started = time.perf_counter()
            output = _score_single_detector(detector, data, text)
            inference_seconds[detector] = inference_seconds.get(detector, 0.0) + (time.perf_counter() - detector_started)
            raw[detector] = output
            if not output.get("available"):
                errors.append(
                    {
                        "scope": "detector",
                        "detector": detector,
                        "item_id": item_id,
                        "failure_mode": "detector_unavailable",
                        "message": str(output.get("error") or "detector unavailable"),
                    }
                )
            signals.append(
                {
                    "detector": detector,
                    "available": bool(output.get("available", False)),
                    "score": float(output.get("score") or 0.0),
                    "confidence": float(output.get("confidence") or 0.0),
                    "label": str(output.get("label") or ("unavailable" if not output.get("available") else "lower_risk")),
                    "raw_result": output,
                    "error": output.get("error"),
                }
            )
        available_scores = [signal["score"] for signal in signals if signal["available"]]
        mean_score = statistics.mean(available_scores) if available_scores else 0.0
        median_score = statistics.median(available_scores) if available_scores else 0.0
        disagreement = max(available_scores) - min(available_scores) if len(available_scores) > 1 else 0.0
        results.append(
            {
                "id": item_id,
                "candidate_id": item.get("candidate_id"),
                "signals": signals,
                "clustered_signals": [
                    {
                        "cluster": "roberta_cluster",
                        "members": signals,
                        "score": round(mean_score, 4),
                        "median_score": round(median_score, 4),
                        "disagreement": round(disagreement, 4),
                        "unavailable_members": [signal["detector"] for signal in signals if not signal["available"]],
                    }
                ],
                "raw_detector_results": raw,
                "detector_disagreement": round(disagreement, 4),
                "artificiality_risk": round(mean_score, 4),
                "warnings": [f"{signal['detector']} unavailable" for signal in signals if not signal["available"]],
            }
        )
    return {
        "request_id": request_id,
        "profile": profile,
        "device": _device(),
        "results": results,
        "timing": {
            "total_seconds": round(time.perf_counter() - started, 4),
            "model_load_seconds": dict(_MODEL_LOAD_SECONDS),
            "inference_seconds": {key: round(value, 4) for key, value in inference_seconds.items()},
            "batch_size": len(texts),
        },
        "loaded_models": [str(key[0]) for key in _SEQUENCE_MODEL_CACHE.keys()],
        "errors": errors,
    }


def _score_single_detector(detector: str, data: dict, text: str):
    if len(text.encode("utf-8")) > 9_500_000:
        return {"available": False, "detector": detector, "error": "Payload exceeds safe 10MB RunPod Flash limit."}
    if not text.strip():
        return {"available": False, "detector": detector, "error": "Empty text cannot be scored."}
    if detector == "radar":
        return _hf_sequence_detector(data=data, text=text, detector="radar", default_model="Shushant/adal-roberta-detector", default_ai_label_index=0)
    if detector == "openai_roberta":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="openai_roberta",
            default_model="openai-community/roberta-base-openai-detector",
            default_ai_label_index=1,
        )
    if detector == "chatgpt_roberta":
        return _hf_sequence_detector(
            data=data,
            text=text,
            detector="chatgpt_roberta",
            default_model="Hello-SimpleAI/chatgpt-detector-roberta",
            default_ai_label_index=1,
        )
    return {"available": False, "detector": detector, "error": f"Unsupported batch detector: {detector}"}


def _device():
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _softmax_probability(logits, ai_label_index: int) -> float:
    import torch

    probs = torch.softmax(logits, dim=-1)[0]
    ai_label_index = max(0, min(ai_label_index, probs.shape[0] - 1))
    return float(probs[ai_label_index].detach().cpu())


def _resolve_ai_label_index(config, default_ai_label_index: int) -> int:
    labels = getattr(config, "id2label", {}) or {}
    if not labels:
        return default_ai_label_index
    positive_markers = ("ai", "fake", "generated", "machine", "chatgpt", "gpt", "synthetic")
    negative_markers = ("human", "real", "original", "authentic")
    for raw_index, raw_label in labels.items():
        label = str(raw_label).lower()
        if any(marker in label for marker in positive_markers) and not any(marker in label for marker in negative_markers):
            return int(raw_index)
    return default_ai_label_index


def _hf_sequence_detector(*, data: dict, text: str, detector: str, default_model: str, default_ai_label_index: int):
    import torch
    from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

    model_name = str(data.get("model_name") or default_model)
    requested_ai_label_index = data.get("ai_label_index")
    device = _device()
    try:
        cache_key = (model_name, device)
        cached = _SEQUENCE_MODEL_CACHE.get(cache_key)
        if cached is None:
            load_started = time.perf_counter()
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            config = AutoConfig.from_pretrained(
                model_name,
                id2label={0: "LABEL_0", 1: "LABEL_1"},
                label2id={"LABEL_0": 0, "LABEL_1": 1},
            )
            if getattr(config, "id2label", None):
                sanitized_id2label = {int(key): str(value) for key, value in config.id2label.items()}
                config.id2label = sanitized_id2label
                config.label2id = {value: key for key, value in sanitized_id2label.items()}
            model = AutoModelForSequenceClassification.from_pretrained(model_name, config=config)
            model.to(device)
            model.eval()
            _SEQUENCE_MODEL_CACHE[cache_key] = (tokenizer, model)
            _MODEL_LOAD_SECONDS[model_name] = round(time.perf_counter() - load_started, 4)
        else:
            tokenizer, model = cached
            config = model.config
        ai_label_index = (
            int(requested_ai_label_index)
            if requested_ai_label_index is not None
            else _resolve_ai_label_index(config, default_ai_label_index)
        )
        encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=int(data.get("max_length", 512)))
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            output = model(**encoded)
        score = _softmax_probability(output.logits, ai_label_index)
        label = "elevated_risk" if score >= 0.62 else "moderate_risk" if score >= 0.38 else "lower_risk"
        return {
            "available": True,
            "detector": detector,
            "implementation": "hf_sequence_classification",
            "implementation_kind": "model_backed",
            "score": round(score, 4),
            "confidence": round(max(score, 1.0 - score), 4),
            "label": label,
            "model_name": model_name,
            "ai_label_index": ai_label_index,
            "device": device,
        }
    except Exception as error:
        return {
            "available": False,
            "detector": detector,
            "implementation": "hf_sequence_classification",
            "model_name": model_name,
            "error": str(error),
        }


def _causal_lm_loss(model, tokenizer, text: str, device: str, max_length: int) -> float:
    import torch

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    encoded = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    encoded = {key: value.to(device) for key, value in encoded.items()}
    with torch.no_grad():
        output = model(**encoded, labels=encoded["input_ids"])
    return float(output.loss.detach().cpu())


def _binoculars_proxy(data: dict, text: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    performer_name = str(data.get("model_name") or "gpt2")
    observer_name = str(data.get("observer_name") or "distilgpt2")
    max_length = int(data.get("max_length", 512))
    device = _device()
    try:
        performer_tokenizer, performer = _causal_lm_from_cache(performer_name, device, AutoTokenizer, AutoModelForCausalLM)
        performer_loss = _causal_lm_loss(performer, performer_tokenizer, text, device, max_length)

        observer_tokenizer, observer = _causal_lm_from_cache(observer_name, device, AutoTokenizer, AutoModelForCausalLM)
        observer_loss = _causal_lm_loss(observer, observer_tokenizer, text, device, max_length)

        binoculars_score = observer_loss / max(performer_loss, 1e-6)
        risk_score = max(0.0, min(1.0, 1.0 - ((binoculars_score - 0.90) / 0.35)))
        label = "elevated_risk" if risk_score >= 0.62 else "moderate_risk" if risk_score >= 0.38 else "lower_risk"
        return {
            "available": True,
            "detector": "binoculars",
            "implementation": "binoculars_perplexity_proxy",
            "implementation_kind": "approximate_model_signal",
            "score": round(risk_score, 4),
            "confidence": 0.72,
            "label": label,
            "binoculars_score": round(binoculars_score, 6),
            "performer_loss": round(performer_loss, 6),
            "observer_loss": round(observer_loss, 6),
            "model_name": performer_name,
            "observer_name": observer_name,
            "device": device,
        }
    except Exception as error:
        return {
            "available": False,
            "detector": "binoculars",
            "implementation": "binoculars_perplexity_proxy",
            "model_name": performer_name,
            "observer_name": observer_name,
            "error": str(error),
        }


def _ghostbuster_feature_proxy(text: str):
    import math
    import re

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)?", text)
    lowered = [word.lower() for word in words]
    unique_ratio = len(set(lowered)) / max(1, len(lowered))
    sentence_lengths = [len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)?", sentence)) for sentence in sentences] or [0]
    mean_len = sum(sentence_lengths) / max(1, len(sentence_lengths))
    variance = sum((length - mean_len) ** 2 for length in sentence_lengths) / max(1, len(sentence_lengths))
    burstiness = math.sqrt(variance) / max(mean_len, 1e-6)
    generic_markers = sum(
        text.lower().count(marker)
        for marker in ["it is important to note", "in conclusion", "overall", "furthermore", "moreover", "plays a crucial role"]
    )
    risk = 0.22 + max(0.0, 0.58 - unique_ratio) * 0.85 + max(0.0, 0.42 - burstiness) * 0.42 + min(0.18, generic_markers * 0.04)
    score = max(0.0, min(1.0, risk))
    label = "elevated_risk" if score >= 0.62 else "moderate_risk" if score >= 0.38 else "lower_risk"
    return {
        "available": True,
        "detector": "ghostbuster",
        "implementation": "ghostbuster_feature_proxy",
        "implementation_kind": "feature_proxy",
        "score": round(score, 4),
        "confidence": 0.55,
        "label": label,
        "lexical_diversity": round(unique_ratio, 4),
        "sentence_burstiness": round(burstiness, 4),
        "generic_marker_count": generic_markers,
    }


def _causal_lm_from_cache(model_name: str, device: str, tokenizer_class, model_class):
    cache_key = (model_name, device)
    cached = _CAUSAL_LM_CACHE.get(cache_key)
    if cached is not None:
        return cached
    tokenizer = tokenizer_class.from_pretrained(model_name)
    model = model_class.from_pretrained(model_name).to(device)
    model.eval()
    _CAUSAL_LM_CACHE[cache_key] = (tokenizer, model)
    return tokenizer, model
