# RunPod GPU First Call Attempt Log

## Summary

Prepared and executed the first real RunPod GPU detector calls after explicit user approval.

## Changes

- Updated `scripts/runpod_flash/detectors_endpoint.py` to use one queue-based `academic-engine-detectors` endpoint compatible with the pipeline's `Endpoint(id=...).runsync(...)` provider.
- Removed the official Binoculars package dependency from the Flash build because it requires an old `tokenizers<0.14` dependency that does not build through the current Flash packaging path.
- Added detector branches:
  - `binoculars`: causal-LM perplexity proxy using `gpt2`/`distilgpt2`.
  - `mage`: Hugging Face sequence classifier using `yaful/MAGE`.
  - `radar`: Hugging Face sequence classifier using `Shushant/adal-roberta-detector`.
  - `ghostbuster`: feature/stylometry proxy until the official Ghostbuster runtime is integrated.
- Kept GPU target at `GpuGroup.AMPERE_80` for the first real detector call to reduce OOM risk.

## Verification

- `python -m py_compile scripts/runpod_flash/detectors_endpoint.py`: passed.
- `python -m pytest tests/test_detector.py tests/test_pipeline_contract.py`: passed, 22 tests.
- Flash build with Python 3.11:
  - Command: `/private/tmp/academic-engine-binoculars-py311/bin/flash build --exclude torch,torchvision,torchaudio`
  - Result: passed.
  - Archive size: 47.1 MB.
  - Dependencies packaged: 4.

## Blocker

The real deploy command was rejected by the approval layer because it would upload private workspace code/build artifacts to RunPod and create billable production resources.

No GPU call was made and no RunPod resource was created in this attempt.

## Approved Deploy And GPU Calls

After the user explicitly approved uploading the Flash artifact to RunPod and creating billable resources, deployment proceeded.

### Deploys

- `academic-engine-detectors`: created endpoint `5u5smdlx3nmxjg`.
  - First calls returned queued jobs with no output because the local provider did not wait on unfinished `EndpointJob` objects.
- Provider fix:
  - `src/academic_engine/detectors.py` now calls `await job.wait(timeout=...)` when `runsync` returns an unfinished job.
- `academic-engine-detectors-v2`: created endpoint `fkwvb49pz2h7v4`.
  - Fixed queue-handler signature from `detect(data)` to `detect(data=None, **kwargs)`.
  - `flash_ghostbuster` worked.
- `academic-engine-detectors-v3`: created endpoint `1lcy6cfkt68xca`.
  - `flash_ghostbuster`, `flash_binoculars`, and `flash_radar` worked.
  - `flash_mage` failed on the `yaful/MAGE` checkpoint config validation.
- `academic-engine-detectors-v4`: created endpoint `hdksl3o3gukl6w`.
  - Removed `id2label` from HF detector output.
  - `flash_mage` still failed before output due checkpoint config validation.
- `academic-engine-detectors-v5`: created endpoint `0398xhyuiuu9yo`.
  - Tried sanitizing `AutoConfig.id2label` after loading.
  - `flash_mage` still failed.
- `academic-engine-detectors-v6`: created endpoint `f1shb4sn20ero8`.
  - Tried overriding `id2label`/`label2id` directly in `AutoConfig.from_pretrained`.
  - `flash_mage` still failed with the same checkpoint config validation error.

### Working GPU Detector Results

Final usable endpoint for working detectors during this session:

- `ACADEMIC_ENGINE_FLASH_ENDPOINT_ID=1lcy6cfkt68xca` or newer `f1shb4sn20ero8`.

Observed scores on the short political-science sample:

- `flash_ghostbuster`: available, `score=0.3829`, `label=moderate_risk`, implementation `ghostbuster_feature_proxy`.
- `flash_binoculars`: available, `score=0.5644`, `label=moderate_risk`, implementation `binoculars_perplexity_proxy`, device `cuda`.
- `flash_radar`: available, `score=0.5922`, `label=moderate_risk`, model `Shushant/adal-roberta-detector`, device `cuda`.
- `flash_mage`: unavailable; `yaful/MAGE` currently fails on config validation for `id2label` with the Flash/HF runtime.

## Verification After GPU Work

- `python -m pytest`: passed, 31 tests.
