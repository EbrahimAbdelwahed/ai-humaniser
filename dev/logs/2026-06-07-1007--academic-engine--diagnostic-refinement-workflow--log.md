# Diagnostic Refinement Workflow Log

## Summary

Implemented a detector-diagnostic refinement workflow that turns failure modes into bounded rewrite guidance and records the decision path in pipeline artifacts.

## Changed Files

- `src/academic_engine/refinement_diagnostics.py`
- `src/academic_engine/pipeline.py`
- `src/academic_engine/schemas.py`
- `tests/test_refinement_diagnostics.py`
- `tests/test_pipeline_contract.py`
- `dev/plans/2026-06-07-1007--academic-engine--diagnostic-refinement-workflow--plan.md`

## Implementation Notes

- Added `RefinementDiagnostics` with:
  - failure modes
  - detector interpretation
  - rewrite recommendations
  - preservation constraints
  - change budget
  - stylometry summary
- Added special interpretation for `official_fast_detectgpt`.
- Added stylometric failure modes for:
  - low local specificity
  - lexical/structural repetition
  - formulaic academic transitions
  - uniform sentence rhythm
  - generic LLM pattern risk
- Updated `AcademicRewritePipeline.refine()` to:
  - build diagnostics before each refinement cycle
  - render the diagnostics into the refinement prompt
  - rescore the refined candidate
  - accept the refined candidate only when hard gates pass and utility improves or detector risk drops enough without disruptive change
  - reject non-improving refinements as next-cycle baselines
- Updated final report artifacts to include diagnostic refinement data and cycle acceptance state.
- Updated final selection so rejected refinement cycles cannot become the final output.

## Verification

- `python -m py_compile src/academic_engine/refinement_diagnostics.py src/academic_engine/pipeline.py src/academic_engine/schemas.py`
- `python -m pytest tests/test_refinement_diagnostics.py tests/test_pipeline_contract.py tests/test_scoring.py tests/test_detector.py -q`
  - `49 passed`
- `python -m pytest -q`
  - `67 passed`
- Mock end-to-end run:
  - input: `_capitolo2_docx.txt`
  - output: `experiments/thesis_calibration_2026_06_06/results/refinement_workflow_mock_capitolo2.json`
  - result: one diagnostic refinement cycle was generated, diagnosed, rescored, rejected as next baseline, and excluded from final selection.

## RunPod

No RunPod endpoint was deployed in this step. Verification stayed local/mock to avoid GPU cost while stabilizing orchestration logic.

## Follow-Up

- Run one small live pass with DeepSeek plus `official_fast_detectgpt` on RunPod after confirming cost envelope.
- Add a web-app-facing response DTO once the API layer is introduced.

## Continuation

After review, the refinement gate was correct but the workflow had not yet proven that accepted refinements could improve a difficult input. Additional changes:

- Added CLI overrides:
  - `--quality-threshold`
  - `--detector-risk-target`
- Updated diagnostic refinement to retry sequentially when a candidate is rejected without hard-gate failures.
- Aligned the initial refinement target with final-selection preference instead of raw rank only.
- Hardened DeepSeek schema handling by coercing string list fields for candidate revisions.
- Added targeted diagnostic improvement scoring so improvements to specific failure modes can be accepted when preservation holds and detector risk does not materially regress.

Additional verification:

- `python -m pytest -q`
  - `69 passed`
- DeepSeek live high-risk smoke:
  - input: `experiments/thesis_calibration_2026_06_06/inputs/refinement_high_risk_smoke.txt`
  - output artifact: `experiments/thesis_calibration_2026_06_06/results/refinement_workflow_deepseek_high_risk_smoke.json`
  - result: two diagnostic refinement cycles accepted, final selected candidate came from refinement cycle 2, hard gates passed.
- Official Fast-DetectGPT RunPod audit:
  - artifact: `experiments/thesis_calibration_2026_06_06/results/raw_audit.official_fast_detectgpt_refinement_high_risk_smoke.json`
  - original smoke input: `0.6917`, `elevated_risk`
  - final selected output: `0.1984`, `lower_risk`
  - RunPod final state: `No endpoints found`
