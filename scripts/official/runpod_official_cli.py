#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stdin-to-JSON client for a deployed RunPod Flash official detector endpoint.")
    parser.add_argument("--endpoint-id", default=os.environ.get("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID"))
    parser.add_argument("--detector", default="official_binoculars")
    parser.add_argument("--operation", default=None, choices=["health", "model_inventory", "bootstrap", "score"])
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS", "900")))
    parser.add_argument("--env-file", default=".env", help="Optional env file used to load RUNPOD_API_KEY without exposing it in CLI args.")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--observer-model", default=os.environ.get("ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_OBSERVER_MODEL"))
    parser.add_argument("--performer-model", default=os.environ.get("ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_PERFORMER_MODEL"))
    parser.add_argument("--sampling-model-name", default=os.environ.get("ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_SAMPLING_MODEL"))
    parser.add_argument("--scoring-model-name", default=os.environ.get("ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_SCORING_MODEL"))
    return parser.parse_args()


def load_env_file(path: str) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


async def call_endpoint(args: argparse.Namespace, text: str) -> dict:
    try:
        from runpod_flash import Endpoint
    except Exception as error:
        return unavailable("dependency_missing", f"runpod_flash is not installed or importable: {error}")
    operation = args.operation if args.operation != "score" else None
    payload = {
        "detector": args.detector,
        "text": text,
        "timeout_seconds": args.timeout,
        "offline": args.offline,
    }
    if operation:
        payload["operation"] = operation
        if args.detector:
            payload["detectors"] = [args.detector]
    optional = {
        "profile": args.profile,
        "observer_model": args.observer_model,
        "performer_model": args.performer_model,
        "sampling_model_name": args.sampling_model_name,
        "scoring_model_name": args.scoring_model_name,
    }
    payload.update({key: value for key, value in optional.items() if value})
    try:
        endpoint = Endpoint(id=args.endpoint_id)
        job = await endpoint.runsync(payload, timeout=args.timeout)
        if hasattr(job, "output"):
            if not getattr(job, "done", True) and hasattr(job, "wait"):
                job = await job.wait(timeout=args.timeout)
            if getattr(job, "error", None):
                return unavailable("endpoint_error", str(job.error))
            output = job.output
        else:
            output = job
    except Exception as error:
        return unavailable("endpoint_error", str(error))
    if not isinstance(output, dict):
        return unavailable("invalid_output", f"Endpoint returned {type(output).__name__}, expected JSON object.")
    return output


def unavailable(failure_mode: str, error: str) -> dict:
    return {
        "available": False,
        "score": 0.0,
        "confidence": 0.0,
        "label": "unavailable",
        "failure_mode": failure_mode,
        "error": error,
    }


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)
    text = sys.stdin.read().strip()
    if not text and args.operation not in {"health", "model_inventory", "bootstrap"}:
        print("No input text received.", file=sys.stderr)
        return 2
    if not args.endpoint_id:
        print(
            "Missing endpoint id. Pass --endpoint-id or set ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID.",
            file=sys.stderr,
        )
        return 3
    output = asyncio.run(call_endpoint(args, text))
    print(json.dumps(output))
    return 0 if output.get("available") is not False else 4


if __name__ == "__main__":
    raise SystemExit(main())
