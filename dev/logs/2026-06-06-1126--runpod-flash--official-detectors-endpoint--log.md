# Official Detectors Flash Endpoint Log

## Summary

Added a cost-aware RunPod Flash endpoint scaffold for official detector runtimes.

## Changed Files

- `scripts/runpod_flash/official_detectors_endpoint.py`
- `tests/test_runpod_official_endpoint.py`
- `dev/plans/2026-06-06-1126--runpod-flash--official-detectors-endpoint--plan.md`
- `dev/logs/2026-06-06-1126--runpod-flash--official-detectors-endpoint--log.md`

## Implementation Notes

- Endpoint name: `academic-engine-official-detectors-v1`.
- Default GPU policy uses `ADA_24`/`AMPERE_24`, `workers=(0, 1)`, and `idle_timeout=30`.
- No A100/80GB GPU is selected by default.
- Supports batch-friendly `score_batch` requests for:
  - `official_binoculars`
  - `official_fast_detectgpt`
- Returns explicit unavailable payloads with `failure_mode` for empty text, oversized payload, missing wrappers, missing Fast-DetectGPT repo/assets, dependency/import failures, invalid wrapper output, timeouts, and unsupported detectors.
- Ghostbuster official is documented in health/model inventory only. It is not executed by this endpoint; when requested without `OPENAI_API_KEY`, it returns `api_key_missing`.
- The module is import-safe when `runpod_flash` is not installed, which keeps local tests offline-safe.

## Verification

- `python -m py_compile scripts/runpod_flash/official_detectors_endpoint.py`
- `python -m pytest tests/test_official_detector_wrappers.py tests/test_runpod_official_endpoint.py`
- `python -m pytest`

All verification passed locally. No RunPod deploy was performed and no RunPod endpoint was called.
