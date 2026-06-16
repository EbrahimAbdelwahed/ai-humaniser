# Official Flash Predeploy Log

## Summary

Prepared the official detector Flash app for a future billable deploy without deploying or calling RunPod.

## Changed Files

- `dev/plans/2026-06-06-1142--academic-engine--official-flash-predeploy--plan.md`
- `scripts/runpod_flash/official_detectors_endpoint.py`
- `scripts/runpod_flash_official/official_detectors_endpoint.py`
- `scripts/runpod_flash_official/official_wrappers/binoculars_official_cli.py`
- `scripts/runpod_flash_official/official_wrappers/fast_detectgpt_official_cli.py`
- `scripts/runpod_flash_official/README.md`

Worker review also added:

- `dev/logs/2026-06-06-1141--runpod-flash--official-detectors-readiness-review--log.md`

## Findings

The original `scripts/runpod_flash` build was not safe to deploy for official calibration because it included the legacy `detectors_endpoint.py`; the generated handler targeted `academic-engine-detectors-small-v1`, not the official detector endpoint.

The official endpoint initially used a dynamic decorator helper, which Flash did not discover in the isolated app. This was corrected to a static `@Endpoint(...)` decorator, matching the existing working Flash endpoint pattern.

## Build Results

From `scripts/runpod_flash`:

```sh
flash build
```

Result:

- failed because archive exceeded RunPod Flash limit: `546.6 MB / 500 MB`

From isolated `scripts/runpod_flash_official`:

```sh
flash build --no-deps --exclude torch,torchvision,torchaudio
```

Result:

- passed
- artifact: `scripts/runpod_flash_official/.flash/artifact.tar.gz`
- artifact size: about `81M`
- manifest resource: `detect`
- handler: `handler_detect.py`
- GPU ids: `AMPERE_24,ADA_24`
- workers: `0..1`

The slim artifact excludes `torch` and CUDA packages. First live health check must verify whether the Flash base image has the required model runtime. If not, use a prebuilt Docker image or a different dependency strategy that remains under the 500MB artifact limit.

## Verification

```sh
python -m py_compile scripts/runpod_flash/official_detectors_endpoint.py scripts/runpod_flash_official/official_detectors_endpoint.py
python -m pytest tests/test_runpod_official_endpoint.py tests/test_official_detector_wrappers.py -q
python -m pytest
```

Final result: `56 passed`.

## No Billable Work

No `flash deploy` command was run. No RunPod endpoint was created or called.
