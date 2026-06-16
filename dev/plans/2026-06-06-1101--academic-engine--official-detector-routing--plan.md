# Official Detector Routing Plan

## Goal

Add offline-safe official detector provider routing for `official_binoculars`, `official_ghostbuster`, and `official_fast_detectgpt`.

## Scope

- `src/academic_engine/config.py`
- `src/academic_engine/detectors.py`
- `src/academic_engine/scoring.py`
- `tests/test_detector.py`
- `tests/test_scoring.py` if scoring weights/notes need coverage

## Steps

1. Inspect current provider registry, CLI parsing wrappers, detector-set expansion, and tests.
2. Add config/env fields for official detector CLI commands and timeout.
3. Implement normalized official providers with explicit unavailable results when unconfigured or failing.
4. Add detector sets `official` and `local+official`.
5. Add tests for provider selection and unavailable fallback.
6. Run focused tests and write a work log.
