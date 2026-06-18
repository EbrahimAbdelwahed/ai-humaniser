# Direct RunPod Fast-DetectGPT Log

## Context

The deployed UI still marked `official_fast_detectgpt` unavailable while the RunPod endpoint existed and a GPU was allocated. The endpoint was also observed as still initializing, which can make the detector unavailable until bootstrap completes.

The previous web route used a subprocess wrapper (`scripts/official/runpod_official_cli.py`) to call RunPod. That is fragile on Vercel because subprocess packaging/runtime behavior can fail independently from RunPod endpoint health.

## Changes

- Added `RunPodOfficialDetectorProvider`.
- Routed `official_fast_detectgpt` directly through `runpod_flash.Endpoint(id=...).runsync(...)` when `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` is configured.
- Preserved the existing `ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI` fallback when no RunPod endpoint id is configured.
- Updated detector tests for direct RunPod provider selection and CLI fallback.

## Verification

```sh
python -m pytest tests/test_detector.py tests/test_web_app.py -q
python -m py_compile src/academic_engine/detectors.py src/academic_engine/web/app.py
```

Both passed locally.

