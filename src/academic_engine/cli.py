from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from academic_engine.config import EngineConfig
from academic_engine.detectors import detector_providers_from_config
from academic_engine.pipeline import AcademicRewritePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Academic writing refinement engine.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Rewrite one input text file.")
    run_parser.add_argument("input", type=Path)
    run_parser.add_argument("-o", "--output", type=Path, required=True)
    run_parser.add_argument("--mock-provider", action="store_true", help="Use deterministic local provider instead of DeepSeek.")
    run_parser.add_argument("--cycles", type=int, default=2, choices=[1, 2])
    detector_choices = [
        "local",
        "local+hf",
        "hf",
        "community",
        "local+community",
        "official",
        "official-binoculars",
        "official-fast-detectgpt",
        "local+official",
        "flash",
        "local+flash",
        "community+flash",
        "all",
    ]
    run_parser.add_argument("--detectors", choices=detector_choices, default=None, help="Detector set to run. Default: local lightweight ensemble.")
    run_parser.add_argument("--include-hf-detector", action="store_true", help="Also run the optional local HuggingFace detector if installed and cached.")
    run_parser.add_argument("--detector-execution", choices=["sequential", "parallel"], default=None, help="Run detectors sequentially by default, or with bounded parallelism.")
    run_parser.add_argument("--detector-concurrency", type=int, default=None, help="Detector parallelism limit. Capped at 2.")
    run_parser.add_argument("--candidate-generation-concurrency", type=int, default=None, help="Generate one candidate per strategy with bounded parallelism. Default: 1.")
    run_parser.add_argument("--community-candidate-limit", type=int, default=None, help="Run expensive community detectors only on the top-K locally ranked candidates. Default: 2.")
    run_parser.add_argument("--flash-profile", choices=["stable", "model", "experimental", "all"], default=None, help="Flash detector profile. Default: stable.")
    run_parser.add_argument("--quality-threshold", type=float, default=None, help="Override the quality threshold used to decide whether refinement is needed.")
    run_parser.add_argument("--detector-risk-target", type=float, default=None, help="Override the detector-risk target used to decide whether refinement is needed.")

    experiment_parser = subparsers.add_parser("experiment", help="Run all .txt fixtures in a directory.")
    experiment_parser.add_argument("fixture_dir", type=Path)
    experiment_parser.add_argument("-o", "--output", type=Path, required=True)
    experiment_parser.add_argument("--mock-provider", action="store_true")
    experiment_parser.add_argument("--cycles", type=int, default=2, choices=[1, 2])
    experiment_parser.add_argument("--detectors", choices=detector_choices, default=None)
    experiment_parser.add_argument("--include-hf-detector", action="store_true")
    experiment_parser.add_argument("--detector-execution", choices=["sequential", "parallel"], default=None)
    experiment_parser.add_argument("--detector-concurrency", type=int, default=None)
    experiment_parser.add_argument("--candidate-generation-concurrency", type=int, default=None)
    experiment_parser.add_argument("--community-candidate-limit", type=int, default=None)
    experiment_parser.add_argument("--flash-profile", choices=["stable", "model", "experimental", "all"], default=None)
    experiment_parser.add_argument("--quality-threshold", type=float, default=None)
    experiment_parser.add_argument("--detector-risk-target", type=float, default=None)

    calibrate_parser = subparsers.add_parser("calibrate", help="Audit every generated/refined candidate with configured teacher detectors.")
    calibrate_parser.add_argument("input", type=Path)
    calibrate_parser.add_argument("-o", "--output", type=Path, required=True)
    calibrate_parser.add_argument("--mock-provider", action="store_true")
    calibrate_parser.add_argument("--cycles", type=int, default=2, choices=[1, 2])
    calibrate_parser.add_argument("--detectors", choices=detector_choices, default="local+flash")
    calibrate_parser.add_argument("--include-hf-detector", action="store_true")
    calibrate_parser.add_argument("--detector-execution", choices=["sequential", "parallel"], default=None)
    calibrate_parser.add_argument("--detector-concurrency", type=int, default=None)
    calibrate_parser.add_argument("--candidate-generation-concurrency", type=int, default=None)
    calibrate_parser.add_argument("--flash-mode", choices=["calibration", "research"], default="calibration")
    calibrate_parser.add_argument("--flash-profile", choices=["stable", "model", "experimental", "all"], default=None)
    calibrate_parser.add_argument("--quality-threshold", type=float, default=None)
    calibrate_parser.add_argument("--detector-risk-target", type=float, default=None)

    raw_audit_parser = subparsers.add_parser("raw-audit", help="Score one or more text files exactly as provided, without rewriting.")
    raw_audit_parser.add_argument("inputs", type=Path, nargs="+")
    raw_audit_parser.add_argument("-o", "--output", type=Path, required=True)
    raw_audit_parser.add_argument("--detectors", choices=detector_choices, default="local")
    raw_audit_parser.add_argument("--include-hf-detector", action="store_true")
    raw_audit_parser.add_argument("--detector-execution", choices=["sequential", "parallel"], default=None)
    raw_audit_parser.add_argument("--detector-concurrency", type=int, default=None)
    raw_audit_parser.add_argument("--flash-mode", choices=["calibration", "research"], default="calibration")
    raw_audit_parser.add_argument("--flash-profile", choices=["stable", "model", "experimental", "all"], default=None)

    health_parser = subparsers.add_parser("detector-health", help="Ping configured detector providers and write a health report.")
    health_parser.add_argument("-o", "--output", type=Path, default=None)
    health_parser.add_argument("--detectors", choices=detector_choices, default="flash")
    health_parser.add_argument("--mock-provider", action="store_true")
    health_parser.add_argument("--detector-execution", choices=["sequential", "parallel"], default=None)
    health_parser.add_argument("--detector-concurrency", type=int, default=None)
    health_parser.add_argument("--flash-profile", choices=["stable", "model", "experimental", "all"], default=None)
    health_parser.add_argument(
        "--sample-text",
        default="Smith (2021) reports a measured 12% change in student policy support after the intervention.",
        help="Short text sent to detector providers for the health check.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    config = EngineConfig.from_env(
        use_mock_provider=getattr(args, "mock_provider", False) or None,
        max_refinement_cycles=getattr(args, "cycles", None),
        detector_set=args.detectors,
        include_hf_detector=getattr(args, "include_hf_detector", False) or None,
    )
    updates = {}
    if args.detector_execution:
        updates["detector_execution_mode"] = args.detector_execution
    if args.detector_concurrency:
        updates["detector_concurrency"] = max(1, min(2, args.detector_concurrency))
    if getattr(args, "candidate_generation_concurrency", None):
        updates["candidate_generation_concurrency"] = max(1, min(7, args.candidate_generation_concurrency))
    if getattr(args, "community_candidate_limit", None):
        updates["community_candidate_limit"] = max(1, min(8, args.community_candidate_limit))
    if getattr(args, "flash_profile", None):
        from academic_engine.config import FLASH_DETECTOR_PROFILES

        updates["flash_detector_profile"] = args.flash_profile
        updates["flash_detector_names"] = FLASH_DETECTOR_PROFILES[args.flash_profile]
    if getattr(args, "quality_threshold", None) is not None:
        updates["quality_threshold"] = max(0.0, min(1.0, args.quality_threshold))
    if getattr(args, "detector_risk_target", None) is not None:
        updates["detector_risk_target"] = max(0.0, min(1.0, args.detector_risk_target))
    if args.command in {"calibrate", "raw-audit"}:
        updates["flash_mode"] = args.flash_mode
    if updates:
        config = replace(config, **updates)
    if args.command == "detector-health":
        providers = detector_providers_from_config(config)
        results = [provider.analyze(args.sample_text) for provider in providers]
        report = {
            "artifact_type": "academic_engine_detector_health",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "detector_set": config.detector_set,
            "flash_profile": config.flash_detector_profile,
            "flash_detectors": list(config.flash_detector_names),
            "detector_execution_mode": config.detector_execution_mode,
            "available_count": len([result for result in results if result.available]),
            "unavailable_count": len([result for result in results if not result.available]),
            "results": [result.model_dump(mode="json") for result in results],
        }
        payload = json.dumps(report, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
        return 0
    pipeline = AcademicRewritePipeline(config=config)
    if args.command == "run":
        result = pipeline.run_file(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return 0
    if args.command == "experiment":
        summary = pipeline.experiment(args.fixture_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return 0
    if args.command == "calibrate":
        pipeline.calibration_audit(args.input, args.output)
        return 0
    if args.command == "raw-audit":
        pipeline.raw_detector_audit(args.inputs, args.output)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
