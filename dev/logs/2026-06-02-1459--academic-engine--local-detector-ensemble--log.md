# Local Detector Ensemble Log

## Summary

Implemented a lightweight local detector ensemble for CLI diagnostic signals and added an optional HuggingFace detector adapter that only uses locally available dependencies/model files.

## Changed

- Added local detector signals:
  - stylometry/burstiness
  - lexical diversity
  - GLTR-lite/probability-shape
  - repetition/genericity
  - readability/academic-pattern risk
- Kept the legacy heuristic provider as a wrapper over local component scores.
- Added optional `hf_roberta_base_openai_detector` using `transformers` with `local_files_only=True`.
- Added config/env/CLI detector selection:
  - default `local`
  - optional `--include-hf-detector`
  - optional `--detectors local+hf`
- Updated scoring to aggregate available detector signals with documented weights and confidence adjustment.
- Added detector disagreement and unavailable optional detector notes to consensus.
- Added final-report detector details while preserving existing report keys.
- Updated README and `.env.example`.
- Added tests for ensemble availability, HF unavailability, consensus/disagreement, report fields, and preservation behavior.

## Verification

- `python -m pytest`: 14 passed.
- `python -m academic_engine.cli run examples/input/political_science.txt -o /private/tmp/academic-engine-smoke.json --mock-provider --cycles 1`: passed.
- `python -m academic_engine.cli run examples/input/political_science.txt -o /private/tmp/academic-engine-smoke-hf.json --mock-provider --cycles 1 --include-hf-detector`: passed; HF detector recorded unavailable.
- Forced-cycle mock with `quality_threshold=1.0` and `detector_risk_target=0.0`: one refinement cycle, stop reason `max_refinement_cycles_reached`, no hard constraint failures.

## Limits

- Local detector scores are diagnostic heuristics, not calibrated probabilities.
- Optional HuggingFace adapter was verified for graceful unavailability, not against a cached local model.
- No online detector or external API was called.
