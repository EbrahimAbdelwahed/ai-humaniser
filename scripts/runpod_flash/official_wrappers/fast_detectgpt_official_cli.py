#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import importlib.machinery
import json
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace


SUPPORTED_MODEL_PAIRS = {
    "gpt-j-6B_gpt-neo-2.7B",
    "gpt-neo-2.7B_gpt-neo-2.7B",
    "falcon-7b_falcon-7b-instruct",
    "llama3-8b_llama3-8b-instruct",
}


def scalar(value) -> float:
    try:
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)
    except TypeError:
        return float(value[0])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stdin-to-JSON wrapper for the official baoguangsheng/fast-detect-gpt detector.")
    parser.add_argument("--repo", type=Path, required=True, help="Path to a local clone of https://github.com/baoguangsheng/fast-detect-gpt.")
    parser.add_argument("--sampling-model-name", default="gpt-neo-2.7B")
    parser.add_argument("--scoring-model-name", default="gpt-neo-2.7B")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--offline", action="store_true", help="Do not download Hugging Face model files; require local cache.")
    return parser.parse_args()


def install_inference_dependency_stubs() -> None:
    """Stub training/eval-only imports pulled by the official local_infer module."""
    if "datasets" not in sys.modules:
        datasets = types.ModuleType("datasets")
        datasets.__spec__ = importlib.machinery.ModuleSpec("datasets", loader=None)
        sys.modules["datasets"] = datasets
    if "matplotlib" not in sys.modules:
        matplotlib = types.ModuleType("matplotlib")
        pyplot = types.ModuleType("matplotlib.pyplot")
        matplotlib.__spec__ = importlib.machinery.ModuleSpec("matplotlib", loader=None)
        pyplot.__spec__ = importlib.machinery.ModuleSpec("matplotlib.pyplot", loader=None)
        matplotlib.pyplot = pyplot
        sys.modules["matplotlib"] = matplotlib
        sys.modules["matplotlib.pyplot"] = pyplot
    if "sklearn" not in sys.modules:
        sklearn = types.ModuleType("sklearn")
        metrics = types.ModuleType("sklearn.metrics")
        sklearn.__spec__ = importlib.machinery.ModuleSpec("sklearn", loader=None)
        metrics.__spec__ = importlib.machinery.ModuleSpec("sklearn.metrics", loader=None)

        def _unused_metric(*_args, **_kwargs):
            raise RuntimeError("Fast-DetectGPT inference wrapper does not support evaluation metrics.")

        metrics.roc_curve = _unused_metric
        metrics.precision_recall_curve = _unused_metric
        metrics.auc = _unused_metric
        sklearn.metrics = metrics
        sys.modules["sklearn"] = sklearn
        sys.modules["sklearn.metrics"] = metrics


def main() -> int:
    args = parse_args()
    text = sys.stdin.read().strip()
    if not text:
        print("No input text received.", file=sys.stderr)
        return 2
    pair = f"{args.sampling_model_name}_{args.scoring_model_name}"
    if pair not in SUPPORTED_MODEL_PAIRS:
        print(
            f"Unsupported Fast-DetectGPT calibrated model pair {pair!r}. "
            f"Supported pairs: {', '.join(sorted(SUPPORTED_MODEL_PAIRS))}",
            file=sys.stderr,
        )
        return 3
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    scripts_dir = args.repo / "scripts"
    if not (scripts_dir / "local_infer.py").exists():
        print(f"Fast-DetectGPT scripts/local_infer.py not found under {args.repo}", file=sys.stderr)
        return 4
    install_inference_dependency_stubs()
    sys.path.insert(0, str(scripts_dir))
    try:
        with contextlib.redirect_stdout(sys.stderr):
            from local_infer import FastDetectGPT
    except Exception as error:
        print(f"Official Fast-DetectGPT import failed. Install repo requirements in this Python env: {error}", file=sys.stderr)
        return 5
    runtime_args = SimpleNamespace(
        sampling_model_name=args.sampling_model_name,
        scoring_model_name=args.scoring_model_name,
        device=args.device,
        cache_dir=args.cache_dir or str(args.repo / "cache"),
    )
    try:
        with contextlib.redirect_stdout(sys.stderr):
            detector = FastDetectGPT(runtime_args)
            probability, criterion, ntokens = detector.compute_prob(text)
    except Exception as error:
        print(f"Official Fast-DetectGPT execution failed: {error}", file=sys.stderr)
        return 6
    score = max(0.0, min(1.0, scalar(probability)))
    print(
        json.dumps(
            {
                "score": score,
                "confidence": 0.76,
                "label": "elevated_risk" if score >= 0.5 else "lower_risk",
                "ai_probability": score,
                "criterion": scalar(criterion),
                "ntokens": int(ntokens),
                "sampling_model_name": args.sampling_model_name,
                "scoring_model_name": args.scoring_model_name,
                "device": args.device,
                "implementation": "official_baoguangsheng_fast_detect_gpt",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
