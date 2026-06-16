# RunPod Flash Official Fast-DetectGPT Calibration Log

Continued official GPU detector calibration after explicit user approval to send the three thesis-derived texts to RunPod.

## RunPod State

- Deployed only cost-controlled official Flash endpoints using `ADA_24`, `AMPERE_24`, `AMPERE_16`, workers `(0, 1)`, idle timeout `30`.
- No 80GB GPU was used.
- Final verification: `flash undeploy list` returned `No endpoints found.`

## Detector Results

### Official Binoculars Qwen profile

Runtime:

- observer: `Qwen/Qwen2.5-1.5B`
- performer: `Qwen/Qwen2.5-1.5B-Instruct`

Result artifact:

- `experiments/thesis_calibration_2026_06_06/results/raw_audit.official_binoculars_qwen_live_v2.json`

Scores:

- `capitolo2_ai_generated`: `0.4444`
- `introduzione_capitolo1_human_first_paragraph`: `0.4708`
- `potere_persuasivo_musica_ai_generated`: `0.6479`

Verdict: stable but weak. It does not separate the fixture because one AI sample scores below the human sample.

### Official Fast-DetectGPT GPT-Neo profile

Runtime:

- sampling model: `gpt-neo-2.7B`
- scoring model: `gpt-neo-2.7B`

Result artifact:

- `experiments/thesis_calibration_2026_06_06/results/raw_audit.official_fast_detectgpt_gptneo_live_v3.json`

Scores:

- `capitolo2_ai_generated`: `0.8512`
- `introduzione_capitolo1_human_first_paragraph`: `0.4152`
- `potere_persuasivo_musica_ai_generated`: `0.9549`

Verdict: useful primary signal for this calibration fixture. Both AI samples score materially above the human sample.

Combined summary:

- `experiments/thesis_calibration_2026_06_06/results/official_detector_calibration_summary.live_v1.json`

## Implementation Changes

- Added `official-fast-detectgpt` detector set to test Fast-DetectGPT without triggering Binoculars or Ghostbuster.
- Changed Fast-DetectGPT default model pair to `gpt-neo-2.7B/gpt-neo-2.7B` for 16/24GB calibration.
- Changed Fast-DetectGPT RunPod bootstrap to install modern minimal inference dependencies instead of the legacy pinned official requirements by default.
- Added environment-driven Fast-DetectGPT model defaults to `scripts/official/runpod_official_cli.py`.
- Added inference-only stubs for Fast-DetectGPT training/evaluation imports (`datasets`, `matplotlib`, `sklearn`) and redirected model loading logs to stderr so stdout remains strict JSON.

## Failure Modes Saved

The calibration summary records these excluded/unstable candidates:

- `official_binoculars_falcon_7b_pair_on_24gb`: CUDA OOM on 24GB.
- `official_binoculars_qwen_1_5b_pair`: stable but poor fixture separation.
- `official_fast_detectgpt_requirements_txt_install`: replaced because the official pinned dependency chain is fragile on current Python.
- `official_ghostbuster_original`: not executed because original Ghostbuster depends on legacy OpenAI completion/logprob access; DeepSeek is not a drop-in substitute without a compatible logprob feature adapter.

## Verification

```sh
python -m py_compile src/academic_engine/detectors.py src/academic_engine/cli.py scripts/official/runpod_official_cli.py scripts/official/fast_detectgpt_official_cli.py scripts/runpod_flash_official/official_detectors_endpoint.py scripts/runpod_flash_official/official_wrappers/fast_detectgpt_official_cli.py
python -m pytest tests/test_detector.py tests/test_runpod_official_endpoint.py tests/test_official_detector_wrappers.py -q
```

Result:

```text
37 passed
```
