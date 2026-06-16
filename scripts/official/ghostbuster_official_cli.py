#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stdin-to-JSON wrapper for the official vivek3141/ghostbuster detector.")
    parser.add_argument("--repo", type=Path, required=True, help="Path to a local clone of https://github.com/vivek3141/ghostbuster.")
    parser.add_argument("--python", default=sys.executable, help="Python executable for the Ghostbuster environment.")
    parser.add_argument("--openai-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = sys.stdin.read().strip()
    if not text:
        print("No input text received.", file=sys.stderr)
        return 2
    classify_py = args.repo / "classify.py"
    if not classify_py.exists():
        print(f"Ghostbuster classify.py not found under {args.repo}", file=sys.stderr)
        return 3
    openai_key = os.environ.get(args.openai_key_env, "")
    if not openai_key:
        print(f"{args.openai_key_env} is required by the official Ghostbuster classify.py runtime.", file=sys.stderr)
        return 4
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        handle.write(text)
        input_path = handle.name
    try:
        completed = subprocess.run(
            [args.python, str(classify_py), "--file", input_path, "--openai_key", openai_key],
            cwd=str(args.repo),
            text=True,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass
    if completed.returncode != 0:
        print(completed.stderr.strip() or completed.stdout.strip() or "Ghostbuster command failed.", file=sys.stderr)
        return completed.returncode
    match = re.search(r"Prediction:\s*\[?([0-9.]+)\]?", completed.stdout)
    if not match:
        print(f"Could not parse Ghostbuster output: {completed.stdout[-500:]}", file=sys.stderr)
        return 5
    score = max(0.0, min(1.0, float(match.group(1))))
    print(
        json.dumps(
            {
                "score": score,
                "confidence": 0.78,
                "label": "elevated_risk" if score >= 0.5 else "lower_risk",
                "ghostbuster_probability": score,
                "implementation": "official_vivek3141_ghostbuster_classify_py",
                "requires_openai_api": True,
                "stdout_tail": completed.stdout[-500:],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
