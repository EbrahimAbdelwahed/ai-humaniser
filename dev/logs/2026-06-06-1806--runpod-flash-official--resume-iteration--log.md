# RunPod Flash Official Resume Iteration Log

Resumed live official detector calibration after network recovery.

## Changes

- Fixed official provider timeout propagation so RunPod-backed official detectors use at least `ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS` as the local subprocess timeout.
- Added `operation=bootstrap` to the official Flash endpoint.
- Added `--operation health|model_inventory|bootstrap|score` support to `scripts/official/runpod_official_cli.py`.
- Added env-configurable official Binoculars model names:
  - `ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_OBSERVER_MODEL`
  - `ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_PERFORMER_MODEL`
- Added `official-binoculars` detector set so `raw-audit` can run only the stabilized official Binoculars signal without triggering Fast-DetectGPT/Ghostbuster.
- Kept endpoint cost-controlled with workers `(0, 1)` and short idle timeout.

## Live Findings

### Falcon default

Official Binoculars with `tiiuae/falcon-7b` and `tiiuae/falcon-7b-instruct` bootstrapped on 24GB but failed scoring with CUDA OOM.

Conclusion: Falcon default needs a larger GPU profile, likely 48GB, but 48GB provisioning stayed `IN_QUEUE` for 600s in this session.

### Qwen iterative profile

Official Binoculars with:

- observer: `Qwen/Qwen2.5-1.5B`
- performer: `Qwen/Qwen2.5-1.5B-Instruct`

successfully scored a short sample on endpoint `76yvtcjecf9dem`:

- `available=true`
- `score=0.1315`
- `binoculars_score=1.1408450603485107`
- `label=lower_risk`

This confirms a stable official model-backed detector path on RunPod for the iterative profile.

## Blocker

The attempted thesis raw-audit on:

- `capitolo2_ai_generated.txt`
- `introduzione_capitolo1_human_first_paragraph.txt`
- `potere_persuasivo_musica_ai_generated.txt`

was blocked by the approval system because it would send private thesis-derived workspace text to RunPod, an external service.

No workaround was attempted.

## RunPod State

Endpoint `detect-fb` / `76yvtcjecf9dem` was undeployed after the blocker.

Final verification:

```text
No endpoints found.
```

No RunPod endpoints were left active.

## Verification

```sh
python -m py_compile src/academic_engine/detectors.py src/academic_engine/cli.py scripts/official/runpod_official_cli.py
python -m pytest tests/test_detector.py tests/test_runpod_official_endpoint.py tests/test_official_detector_wrappers.py -q
```

Result: `36 passed`.
