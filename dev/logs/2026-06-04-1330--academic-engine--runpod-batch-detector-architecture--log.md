# RunPod Batch Detector Architecture Log

## Summary

Implemented offline-safe batch detector architecture for the academic engine without deploying RunPod or calling RunPod/API endpoints.

## Changes

- Added detector registry with `roberta_cluster` as the stable profile signal over:
  - `radar`
  - `openai_roberta`
  - `chatgpt_roberta`
- Added batch detector schemas for request/response, signals, clustered signals, telemetry, and partial failures.
- Added RunPod batch provider abstraction that sends many candidate texts in one `score_batch` request when configured and returns explicit unavailable results offline.
- Updated Flash provider selection so stable Flash exposes `flash_roberta_cluster`, not three independent Flash providers.
- Updated scoring weights and notes so RoBERTa-like models are consumed as one correlated cluster.
- Added excluded candidate audit persistence in final report/artifacts with normalized failure modes.
- Added API-configurable Binoculars/cross-perplexity interface using observer/performer model/base URL/key config and logprobs, with unavailable fallback for missing/incomplete config.
- Updated `scripts/runpod_flash/detectors_endpoint.py` with local-safe `health`, `model_inventory`, and `score_batch` operations, lazy model loading telemetry, per-detector timing, cluster aggregation, and partial failures.
- Added focused tests for registry/profile expansion, batch schema serialization, one batch call for multiple candidates, excluded candidate audit, and Binoculars fake-client behavior.

## Files Changed

- `src/academic_engine/config.py`
- `src/academic_engine/schemas.py`
- `src/academic_engine/detectors.py`
- `src/academic_engine/scoring.py`
- `src/academic_engine/pipeline.py`
- `src/academic_engine/detector_registry.py`
- `src/academic_engine/detector_batch.py`
- `src/academic_engine/candidate_audit.py`
- `scripts/runpod_flash/detectors_endpoint.py`
- `tests/test_detector.py`
- `tests/test_pipeline_contract.py`
- `tests/test_schemas.py`

## Verification

```text
python -m py_compile scripts/runpod_flash/detectors_endpoint.py src/academic_engine/config.py src/academic_engine/detectors.py src/academic_engine/detector_batch.py src/academic_engine/detector_registry.py src/academic_engine/candidate_audit.py src/academic_engine/pipeline.py src/academic_engine/scoring.py src/academic_engine/schemas.py
python -m pytest
```

Result: `38 passed`.

## Coordinator Review Update

After worker completion, coordinator review made the Flash/Binoculars boundary explicit:

- `flash_detector_providers` now routes `roberta_cluster` through the RunPod batch provider and does not route profile-derived `binoculars` through that batch path.
- `scripts/runpod_flash/detectors_endpoint.py` no longer advertises `binoculars` in the batch `calibration` profile. Binoculars remains an API-configurable logprobs provider outside the RunPod batch endpoint, with the legacy endpoint proxy marked experimental.
- Added a regression test that `flash` calibration with `roberta_cluster, binoculars` produces only `flash_roberta_cluster`.

Additional verification:

```text
python -m py_compile src/academic_engine/detectors.py scripts/runpod_flash/detectors_endpoint.py
python -m pytest tests/test_detector.py tests/test_pipeline_contract.py tests/test_schemas.py
python -m pytest
```

Result: `39 passed`.

## Constraints

- No RunPod deploy was performed.
- No RunPod endpoint was called.
- No billable API call was made.
- No `.env` secret values were printed.
- GPU remains optional and offline-safe.
