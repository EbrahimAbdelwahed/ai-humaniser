# RunPod Flash Official Code-Only Bootstrap Tests Log

## Summary

Updated bounded test and documentation coverage for the isolated official RunPod Flash detector app.

## Changed Files

- `tests/test_runpod_official_endpoint.py`
- `scripts/runpod_flash_official/README.md`
- `dev/logs/2026-06-06-1737--runpod-flash-official--code-only-bootstrap-tests--log.md`

## Notes

- Tests now import `scripts.runpod_flash_official.official_detectors_endpoint`.
- README now documents the code-only artifact contract, small upload intent, 24GB GPU policy, `0..1` worker scale, opt-in runtime bootstrap, and explicit failure modes.
- Added tests for README contract terms, packaged wrapper path, wrapper-missing failure, dependency-missing failure, model-assets-missing failure, and generic detector unavailable failure.
- No `src/academic_engine` files or endpoint logic were changed.

## Verification

- `python -m py_compile scripts/runpod_flash_official/official_detectors_endpoint.py`
- `python -m pytest tests/test_runpod_official_endpoint.py -q`
- `python -m pytest tests/test_runpod_official_endpoint.py tests/test_official_detector_wrappers.py -q`
