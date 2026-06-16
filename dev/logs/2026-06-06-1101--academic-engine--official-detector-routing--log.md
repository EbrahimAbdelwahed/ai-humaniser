# Official Detector Routing Log

## Summary

Implemented offline-safe official detector routing for:

- `official_binoculars`
- `official_ghostbuster`
- `official_fast_detectgpt`

## Changed Files

- `src/academic_engine/config.py`
- `src/academic_engine/detectors.py`
- `src/academic_engine/scoring.py`
- `tests/test_detector.py`
- `tests/test_scoring.py`
- `dev/plans/2026-06-06-1101--academic-engine--official-detector-routing--plan.md`

## Details

- Added config/env fields for official detector wrapper commands:
  - `ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI`
  - `ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI`
  - `ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI`
  - `ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS`
- Added `OfficialDetectorProvider`, reusing `parse_cli_detector_output` and `analyze_with_cli_provider`.
- Added detector sets:
  - `official`
  - `local+official`
- Official providers return explicit unavailable `DetectorResult` values when no local CLI command is configured.
- Added scoring weights and notes for available official signals.

## Verification

Passed:

```sh
python -m pytest tests/test_detector.py tests/test_scoring.py
python -m py_compile src/academic_engine/config.py src/academic_engine/detectors.py src/academic_engine/scoring.py
```

## Caveats

- No detector dependencies were installed.
- No network calls, RunPod calls, deployments, or `.env` secret printing were performed.
- Official detector execution requires local wrapper commands that read stdin and print JSON or a numeric risk score.
