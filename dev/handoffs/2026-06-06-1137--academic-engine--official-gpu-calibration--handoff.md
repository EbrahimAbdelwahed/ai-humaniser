# Official GPU Calibration Handoff

## Current State

Official detector integration is wired and locally verified, but the goal is not complete because calibration-grade official model signals have not yet run on the thesis fixture.

## Ready For Deploy

- Endpoint source: `scripts/runpod_flash_official/official_detectors_endpoint.py`
- Flash app directory: `scripts/runpod_flash_official`
- Endpoint name: `academic-engine-official-detectors-v1`
- GPU policy: `ADA_24` or `AMPERE_24`
- Workers: `(0, 1)`
- Idle timeout: `30s`
- Client: `scripts/official/runpod_official_cli.py`
- Autowire env: `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID`

## Calibration Fixture

Use:

- `experiments/thesis_calibration_2026_06_06/samples/capitolo2_ai_generated.txt`
- `experiments/thesis_calibration_2026_06_06/samples/introduzione_capitolo1_human_first_paragraph.txt`
- `experiments/thesis_calibration_2026_06_06/samples/potere_persuasivo_musica_ai_generated.txt`

## Recommended First GPU Run

1. Deploy the official endpoint only after explicit approval.
2. Configure `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID`.
3. Run detector health with `--detectors official`.
4. Run raw audit with `--detectors local+official`.
5. Check whether AI-generated samples score materially higher than the human sample.

## Known Limits

- Local Binoculars tiny-model smoke is plumbing-only and not useful as a detector signal.
- Fast-DetectGPT needs calibrated large model pairs; the wrapper rejects unsupported tiny pairs.
- Ghostbuster official is not autowired because it requires OpenAI API legacy logprob access.
- The deployable official Flash artifact is the isolated app under `scripts/runpod_flash_official`, not the mixed legacy directory under `scripts/runpod_flash`.
- Predeploy build command that passed: `flash build --no-deps --exclude torch,torchvision,torchaudio`.
- The slim artifact is about `81M` and excludes `torch`; live health must verify base-image dependencies.
