# Hard Gates, Raw Audit, and Candidate Generation Follow-up

Implemented follow-up fixes after the blind thesis GPU test.

## Changes

- Hard gate safety:
  - Final selection now returns `preservation-fallback-original` when no generated/refined candidate passes hard preservation gates.
  - If late final rescoring ever exposes hard failures, the pipeline also falls back to the original text.
  - Stop reason is `blocked_no_safe_candidate_preserved_original`.
  - The report warns that no generated candidate passed preservation gates.

- Raw detector audit:
  - Added `AcademicRewritePipeline.raw_detector_audit(...)`.
  - Added CLI command:

```sh
python -m academic_engine.cli raw-audit <input...> -o <output.json> --detectors local
```

- Candidate generation:
  - Replaced one large `CandidateRevisions` generation call with one `CandidateRevision` call per strategy.
  - Strategies are still the same seven existing strategies.
  - Added bounded config/env/CLI parallelism:
    - `ACADEMIC_ENGINE_CANDIDATE_GENERATION_CONCURRENCY`
    - `--candidate-generation-concurrency`

- Detector weighting:
  - Reduced `flash_roberta_cluster` weight from `0.72` to `0.35`.
  - Rationale: in the blind test, the RoBERTa cluster did not separate human and DeepSeek samples well and should remain a weak supporting model-based signal.

- Mainstream calibration snippets:
  - Created `experiments/blind_thesis_2026_06_04/mainstream_detector_snippets_short.md`.
  - Contains the two 520-word snippets with blind labels and source type.

## Artifacts

- `experiments/blind_thesis_2026_06_04/mainstream_detector_snippets_short.md`
- `experiments/blind_thesis_2026_06_04/results/raw_audit_cli.short.local.json`

Local raw audit after downweight/local-only:

- `sample_a`: risk `0.2837`, consensus `lower_risk`
- `sample_b`: risk `0.4363`, consensus `moderate_risk`

## Verification

```sh
python -m py_compile src/academic_engine/config.py src/academic_engine/llm.py src/academic_engine/pipeline.py src/academic_engine/cli.py
python -m academic_engine.cli raw-audit experiments/blind_thesis_2026_06_04/samples_short/sample_a.txt experiments/blind_thesis_2026_06_04/samples_short/sample_b.txt -o experiments/blind_thesis_2026_06_04/results/raw_audit_cli.short.local.json --detectors local
python -m pytest
```

Result: `42 passed`.

## Remaining Work

- Re-run a full DeepSeek pipeline smoke on a longer chapter excerpt to confirm one-candidate-per-call solves the invalid JSON issue in live mode.
- Add stronger GPU detector families beyond the RoBERTa cluster; current stable GPU profile is still too narrow.
- Use mainstream detector results from the two snippets to calibrate local weights and thresholds.
