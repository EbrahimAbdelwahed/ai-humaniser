# Official Detector Stack Calibration Log

## Summary

Coordinated low-reasoning workers and implemented the official detector plumbing for:

- `official_binoculars`
- `official_ghostbuster`
- `official_fast_detectgpt`

Prepared thesis-derived calibration fixtures and recorded why the current local runtime is not yet calibration-grade.

## Changed Files

- `src/academic_engine/config.py`
- `src/academic_engine/detectors.py`
- `src/academic_engine/scoring.py`
- `src/academic_engine/cli.py`
- `scripts/official/binoculars_official_cli.py`
- `scripts/official/ghostbuster_official_cli.py`
- `scripts/official/fast_detectgpt_official_cli.py`
- `scripts/official/runpod_official_cli.py`
- `scripts/runpod_flash/official_detectors_endpoint.py`
- `tests/test_cli.py`
- `tests/test_detector.py`
- `tests/test_scoring.py`
- `tests/test_official_detector_wrappers.py`
- `tests/test_runpod_official_endpoint.py`
- `experiments/thesis_calibration_2026_06_06/manifest.json`
- `experiments/thesis_calibration_2026_06_06/samples/capitolo2_ai_generated.txt`
- `experiments/thesis_calibration_2026_06_06/samples/introduzione_capitolo1_human_first_paragraph.txt`
- `experiments/thesis_calibration_2026_06_06/samples/potere_persuasivo_musica_ai_generated.txt`
- `experiments/thesis_calibration_2026_06_06/results/raw_audit.local.json`
- `experiments/thesis_calibration_2026_06_06/results/raw_audit.local_official.unconfigured.json`
- `experiments/thesis_calibration_2026_06_06/results/detector_health.official_wrappers.uninstalled.json`
- `experiments/thesis_calibration_2026_06_06/results/detector_health.official_binoculars_tiny.json`
- `experiments/thesis_calibration_2026_06_06/results/detector_health.official_binoculars_tiny.tmpcache.json`
- `experiments/thesis_calibration_2026_06_06/results/raw_audit.local_official.binoculars_tiny.json`
- `experiments/thesis_calibration_2026_06_06/results/official_detector_runtime_failure_modes.json`

## Results

Local-only baseline still weakly separates the samples:

- `capitolo2_ai_generated`: `0.4462`, moderate risk
- `introduzione_capitolo1_human_first_paragraph`: `0.4010`, moderate risk
- `potere_persuasivo_musica_ai_generated`: `0.4353`, moderate risk

With official wrappers unconfigured, all three official providers return explicit unavailable results.

With the previous Python 3.11 Binoculars venv and a tiny model smoke configuration, `official_binoculars` runs but does not separate the fixture:

- `capitolo2_ai_generated`: `official_binoculars=0.4447`
- `introduzione_capitolo1_human_first_paragraph`: `official_binoculars=0.4438`
- `potere_persuasivo_musica_ai_generated`: `official_binoculars=0.4440`

This validates plumbing only. It is not calibration-grade.

## Runtime Findings

- Official Binoculars default calibrated models are Falcon-7B/Falcon-7B-Instruct. Local tiny-model smoke is not meaningful for thesis calibration.
- Official Fast-DetectGPT calibrated pairs require `gpt-neo-2.7B`, `gpt-j-6B`, Falcon-7B, or Llama3-8B class models. The wrapper rejects unsupported tiny pairs before loading to avoid accidental uncalibrated outputs.
- Official Ghostbuster `classify.py` requires `OPENAI_API_KEY` and legacy OpenAI completion/logprob access. It was not run on thesis text in this local pass.
- One-shot CLI model loading is too slow for web-app latency. Official model detectors need a persistent or batch GPU runtime.

## RunPod Work

Added `scripts/runpod_flash/official_detectors_endpoint.py` as a cost-aware Flash endpoint scaffold:

- endpoint name: `academic-engine-official-detectors-v1`
- GPU policy: `ADA_24` or `AMPERE_24`
- workers: `(0, 1)`
- idle timeout: `30s`
- no 80GB GPU default
- batch scoring for `official_binoculars` and `official_fast_detectgpt`
- explicit unavailable/failure-mode payloads

Added `scripts/official/runpod_official_cli.py` so core pipeline official providers can call a deployed endpoint through `ACADEMIC_ENGINE_OFFICIAL_*_CLI` without changing `src/academic_engine`.

No RunPod deployment or billable endpoint call was performed in this pass.

## Verification

```sh
python -m py_compile scripts/official/binoculars_official_cli.py scripts/official/ghostbuster_official_cli.py scripts/official/fast_detectgpt_official_cli.py scripts/official/runpod_official_cli.py scripts/runpod_flash/official_detectors_endpoint.py
python -m pytest
```

Final result: `53 passed`.

## Next Step

Deploy the cost-aware official detector endpoint only after explicit approval. First GPU calibration should use:

- `official_fast_detectgpt` with `gpt-neo-2.7B_gpt-neo-2.7B`
- `official_binoculars` with calibrated models only if 24GB VRAM is enough
- `official_ghostbuster` only if legacy OpenAI logprob access is confirmed

Then rerun `raw-audit` on the three thesis calibration samples and require the AI-generated samples to score materially above the human sample before treating the detector stack as stable.
