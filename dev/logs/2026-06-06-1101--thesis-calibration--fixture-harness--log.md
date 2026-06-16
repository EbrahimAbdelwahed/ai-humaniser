# Thesis Calibration Fixture Harness Log

## Summary

Prepared local-only thesis calibration fixtures from the three provided inputs and ran the current raw detector audit with `--detectors local`.

## Created Files

- `experiments/thesis_calibration_2026_06_06/manifest.json`
- `experiments/thesis_calibration_2026_06_06/samples/capitolo2_ai_generated.txt`
- `experiments/thesis_calibration_2026_06_06/samples/introduzione_capitolo1_human_first_paragraph.txt`
- `experiments/thesis_calibration_2026_06_06/samples/potere_persuasivo_musica_ai_generated.txt`
- `experiments/thesis_calibration_2026_06_06/results/raw_audit.local.json`

## Fixture Manifest

- `capitolo2_ai_docx_txt`: AI-generated, `provided_txt`, 2247 words, sha256 `772b1ce28a5fd1f2c939a513db724bb2ccd9a8c8923d201e00c083ee8edcb7e7`
- `introduzione_capitolo1_human_first_paragraph`: human-generated, `provided_txt`, 1186 words, sha256 `932302daf7dfc2321c3c34c012e58d32b42c960587360792df4c5375d316f3fb`
- `potere_persuasivo_musica_ai_docx`: AI-generated, `docx_extracted`, 1203 words, sha256 `ee029717fbde78ec71ecd99102aec7c38d50f3ac124b2d9b1c0b8c1943b8ee9b`

## Baseline Local Scores

- `capitolo2_ai_generated`: risk `0.4462`, consensus `moderate_risk`, disagreement `0.5`
- `introduzione_capitolo1_human_first_paragraph`: risk `0.401`, consensus `moderate_risk`, disagreement `0.5`
- `potere_persuasivo_musica_ai_generated`: risk `0.4353`, consensus `moderate_risk`, disagreement `0.5`

## Verification

```sh
python -m academic_engine.cli raw-audit experiments/thesis_calibration_2026_06_06/samples/capitolo2_ai_generated.txt experiments/thesis_calibration_2026_06_06/samples/introduzione_capitolo1_human_first_paragraph.txt experiments/thesis_calibration_2026_06_06/samples/potere_persuasivo_musica_ai_generated.txt -o experiments/thesis_calibration_2026_06_06/results/raw_audit.local.json --detectors local
python -m pytest
```

Both commands passed.

## Caveats

- DOCX extraction used local WordprocessingML parsing; no network, API, or GPU calls were made.
- Local heuristic scores are diagnostic and did not separate the provided AI-generated samples strongly from the provided human sample.
