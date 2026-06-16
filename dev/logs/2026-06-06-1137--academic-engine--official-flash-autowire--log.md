# Official Flash Autowire Log

## Summary

Moved the official detector stack closer to deployable calibration by adding one-env RunPod routing and making the official Flash endpoint artifact less fragile.

## Changed Files

- `src/academic_engine/config.py`
- `src/academic_engine/detectors.py`
- `.env.example`
- `scripts/official/runpod_official_cli.py`
- `scripts/runpod_flash/official_detectors_endpoint.py`
- `scripts/runpod_flash/official_wrappers/binoculars_official_cli.py`
- `scripts/runpod_flash/official_wrappers/fast_detectgpt_official_cli.py`
- `tests/test_detector.py`
- `tests/test_runpod_official_endpoint.py`
- `experiments/thesis_calibration_2026_06_06/results/detector_health.official_flash_autowire.dummy.json`

## Implementation Notes

- Added `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID`.
- Added `ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS`.
- If `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` is present and detector-specific official CLIs are absent:
  - `official_binoculars` auto-routes through `scripts/official/runpod_official_cli.py`.
  - `official_fast_detectgpt` auto-routes through `scripts/official/runpod_official_cli.py`.
  - `official_ghostbuster` remains unconfigured because the official runtime depends on legacy OpenAI logprob access.
- `runpod_official_cli.py` now reads `.env` itself so a subprocess can access `RUNPOD_API_KEY` without exposing the key in command arguments or reports.
- The official Flash endpoint now prefers wrappers vendored under `scripts/runpod_flash/official_wrappers/`, making the endpoint artifact less dependent on sibling directories.
- Structured unavailable JSON from nonzero wrapper exits is preserved as an unavailable detector result instead of being reduced to an opaque subprocess failure.

## Verification

```sh
python -m py_compile src/academic_engine/config.py src/academic_engine/detectors.py scripts/official/runpod_official_cli.py scripts/runpod_flash/official_detectors_endpoint.py scripts/runpod_flash/official_wrappers/binoculars_official_cli.py scripts/runpod_flash/official_wrappers/fast_detectgpt_official_cli.py
python -m pytest tests/test_detector.py tests/test_official_detector_wrappers.py tests/test_runpod_official_endpoint.py
python -m pytest
```

Final result: `56 passed`.

## Dry Run

Command:

```sh
env ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=dummy-endpoint ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS=5 python -m academic_engine.cli detector-health --detectors official -o experiments/thesis_calibration_2026_06_06/results/detector_health.official_flash_autowire.dummy.json
```

Result:

- `official_binoculars`: unavailable, `failure_mode=endpoint_error`
- `official_fast_detectgpt`: unavailable, `failure_mode=endpoint_error`
- `official_ghostbuster`: unavailable, intentionally not autowired

This proves the pipeline reaches the RunPod client path and records endpoint failures without traceback noise.

## Next Step

Deploy `scripts/runpod_flash/official_detectors_endpoint.py` with RunPod Flash after explicit billing approval, then configure:

```text
ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=<deployed-endpoint-id>
ACADEMIC_ENGINE_DETECTORS=local+official
```

First calibration should prefer `official_fast_detectgpt` with `gpt-neo-2.7B_gpt-neo-2.7B`; treat Binoculars calibrated Falcon defaults as second step if 24GB VRAM is sufficient.
