from __future__ import annotations

import argparse
import json
import os
import sys


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def risk_from_binoculars_score(score: float) -> float:
    return 1.0 - clamp((score - 0.75) / 0.45)


def label_from_risk(score: float) -> str:
    if score >= 0.62:
        return "elevated_risk"
    if score >= 0.38:
        return "moderate_risk"
    return "lower_risk"


def main() -> int:
    parser = argparse.ArgumentParser(description="stdin-to-JSON wrapper for the official Binoculars detector.")
    parser.add_argument("--observer", default=os.getenv("ACADEMIC_ENGINE_BINOCULARS_OBSERVER", "tiiuae/falcon-7b"))
    parser.add_argument("--performer", default=os.getenv("ACADEMIC_ENGINE_BINOCULARS_MODEL", "tiiuae/falcon-7b-instruct"))
    parser.add_argument("--mode", default=os.getenv("ACADEMIC_ENGINE_BINOCULARS_MODE", "low-fpr"))
    parser.add_argument("--max-token-observed", type=int, default=int(os.getenv("ACADEMIC_ENGINE_BINOCULARS_MAX_TOKENS", "512")))
    parser.add_argument("--cache-dir", default=os.getenv("ACADEMIC_ENGINE_HF_CACHE_DIR"))
    parser.add_argument("--no-bfloat16", action="store_true")
    args = parser.parse_args()

    if args.cache_dir:
        os.environ.setdefault("HF_HOME", args.cache_dir)
        os.environ.setdefault("TRANSFORMERS_CACHE", args.cache_dir)
        os.environ.setdefault("HF_HUB_CACHE", os.path.join(args.cache_dir, "hub"))

    text = sys.stdin.read().strip()
    if not text:
        raise SystemExit("No input text received on stdin.")

    from binoculars import Binoculars

    detector = Binoculars(
        observer_name_or_path=args.observer,
        performer_name_or_path=args.performer,
        use_bfloat16=not args.no_bfloat16,
        max_token_observed=args.max_token_observed,
        mode=args.mode,
    )
    raw_score = detector.compute_score(text)
    binoculars_score = float(raw_score[0] if isinstance(raw_score, list) else raw_score)
    risk = risk_from_binoculars_score(binoculars_score)
    print(
        json.dumps(
            {
                "score": risk,
                "confidence": 0.78,
                "label": label_from_risk(risk),
                "binoculars_score": binoculars_score,
                "observer": args.observer,
                "performer": args.performer,
                "mode": args.mode,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
