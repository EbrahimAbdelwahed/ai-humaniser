# Flash Detector Reliability Log

## Summary

Made Flash detector access more reliable and explicit for the refinement pipeline.

## Changes

- Added Flash detector profiles in `src/academic_engine/config.py`:
  - `stable`: `radar`, `binoculars`
  - `model`: `radar`
  - `experimental`: `radar`, `binoculars`, `ghostbuster`
  - `all`: `radar`, `binoculars`, `ghostbuster`, `mage`
- Changed the default Flash profile to `stable`, so MAGE is not called by default because it is a known failing detector in the current runtime.
- Added `academic-engine detector-health` to ping configured detector providers and write a JSON health report.
- Added `--flash-profile` to `run`, `experiment`, `calibrate`, and `detector-health`.
- Added Flash provider metadata:
  - `flash_profile`
  - `stable_for_pipeline`
- Updated `scripts/runpod_flash/detectors_endpoint.py`:
  - endpoint name is now `academic-engine-detectors-v7`
  - added `detector=health`
  - added model caching for sequence-classification and causal-LM detector paths
  - added endpoint-side `implementation_kind` metadata
- Updated tests for the new stable Flash defaults and experimental profile.

## RunPod State

Recommended endpoint for current pipeline work:

```text
r1qf9lfyjy22ao
```

Health check on endpoint `r1qf9lfyjy22ao` with `--flash-profile stable`:

- available: `2`
- unavailable: `0`
- `flash_radar`: available, CUDA, `Shushant/adal-roberta-detector`, `implementation_kind=model_backed`
- `flash_binoculars`: available, CUDA, `gpt2`/`distilgpt2`, `implementation_kind=approximate_model_signal`

Second warm health check completed in about `2.5s` end-to-end for both stable Flash detectors.

## Proxy Clarification

- `flash_radar` is the strongest current GPU detector signal because it is a real Hugging Face sequence-classification model.
- `flash_binoculars` is not the official Binoculars package. It is a GPU perplexity-ratio approximation using causal language models. It is useful as a signal, but it should not be described as official Binoculars.
- `flash_ghostbuster` is a feature/stylometry proxy and is excluded from the stable profile.
- `flash_mage` is excluded from stable/experimental default use unless explicitly selected through `all`; the current `yaful/MAGE` load path has failed config validation in Flash.

## Verification

```text
python -m pytest
```

Result: `32 passed`.
