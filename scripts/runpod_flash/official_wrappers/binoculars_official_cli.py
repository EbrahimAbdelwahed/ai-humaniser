#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


BINOCULARS_ACCURACY_THRESHOLD = 0.9015310749276843
BINOCULARS_FPR_THRESHOLD = 0.8536432310785527


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def risk_from_binoculars_score(score: float) -> float:
    # In the official implementation lower Binoculars scores indicate AI risk.
    return clamp(1.0 - ((score - 0.75) / 0.45))


def label_from_score(score: float, mode: str) -> str:
    threshold = BINOCULARS_FPR_THRESHOLD if mode == "low-fpr" else BINOCULARS_ACCURACY_THRESHOLD
    return "elevated_risk" if score < threshold else "lower_risk"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stdin-to-JSON wrapper for the official ahans30/Binoculars detector.")
    parser.add_argument("--repo", type=Path, default=None, help="Path to a local clone of https://github.com/ahans30/Binoculars.")
    parser.add_argument("--observer-model", default="tiiuae/falcon-7b")
    parser.add_argument("--performer-model", default="tiiuae/falcon-7b-instruct")
    parser.add_argument("--mode", choices=["low-fpr", "accuracy"], default="low-fpr")
    parser.add_argument("--max-token-observed", type=int, default=512)
    parser.add_argument("--no-bfloat16", action="store_true")
    parser.add_argument("--offline", action="store_true", help="Do not download Hugging Face model files; require local cache.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = sys.stdin.read().strip()
    if not text:
        print("No input text received.", file=sys.stderr)
        return 2
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if args.repo:
        sys.path.insert(0, str(args.repo))
    try:
        from binoculars import Binoculars
    except Exception as error:
        print(f"Official Binoculars import failed. Install the repo/package or pass --repo: {error}", file=sys.stderr)
        return 3
    try:
        detector = Binoculars(
            observer_name_or_path=args.observer_model,
            performer_name_or_path=args.performer_model,
            use_bfloat16=not args.no_bfloat16,
            max_token_observed=args.max_token_observed,
            mode=args.mode,
        )
        raw_score = detector.compute_score(text)
    except Exception as error:
        print(f"Official Binoculars execution failed: {error}", file=sys.stderr)
        return 4
    score = float(raw_score[0] if isinstance(raw_score, list) else raw_score)
    risk = risk_from_binoculars_score(score)
    print(
        json.dumps(
            {
                "score": risk,
                "confidence": 0.78,
                "label": label_from_score(score, args.mode),
                "binoculars_score": score,
                "mode": args.mode,
                "observer_model": args.observer_model,
                "performer_model": args.performer_model,
                "max_token_observed": args.max_token_observed,
                "implementation": "official_ahans30_binoculars",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
