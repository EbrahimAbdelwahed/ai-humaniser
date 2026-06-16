# Web Prototype Remote Endpoint Policy Log

Date: 2026-06-11

## Summary

Implemented backend-side controls for using the Fast-DetectGPT/RunPod endpoint from the web app.

The browser still talks only to FastAPI. FastAPI now decides whether a request can use the remote detector, whether it should fall back to local detectors, and whether a detector result can be served from cache.

## Changed Files

- `src/academic_engine/web/app.py`
- `src/academic_engine/web/static/app.js`
- `tests/test_web_app.py`
- `dev/plans/2026-06-11-2131--web-prototype--remote-endpoint-policy--plan.md`
- `dev/logs/2026-06-11-2131--web-prototype--remote-endpoint-policy--log.md`
- `dev/index.md`

## Backend Behavior

- Added `WebSettings` remote policy fields:
  - `ACADEMIC_ENGINE_ENABLE_REMOTE_DETECTORS`
  - `ACADEMIC_ENGINE_REMOTE_MAX_WORDS`
  - `ACADEMIC_ENGINE_REMOTE_DAILY_LIMIT`
  - `ACADEMIC_ENGINE_REMOTE_PER_IP_DAILY_LIMIT`
  - `ACADEMIC_ENGINE_REMOTE_MIN_INTERVAL_SECONDS`
  - `ACADEMIC_ENGINE_REMOTE_CACHE_TTL_HOURS`
  - `ACADEMIC_ENGINE_REMOTE_MAX_CONCURRENT_JOBS`
- Added `RemoteEndpointState`:
  - global daily counter
  - per-client daily counters
  - per-client throttle interval
  - active remote job counter
  - in-memory detector-result cache
- Added remote policy decision flow in `JobRunner.submit`.
- Remote presets fall back to local when:
  - remote detectors are disabled
  - Fast-DetectGPT is not configured
  - input exceeds the remote word limit
  - global daily limit is reached
  - per-client daily limit is reached
  - per-client throttle interval has not elapsed
  - remote concurrency is full
- Added `CachedRemoteDetectorProvider` wrapper for `official_fast_detectgpt`.
- Added `remote_policy` metadata and policy warnings to detection/refinement payloads.
- Added `/health.remote_policy` metadata for frontend display.

## Frontend Behavior

- The context band now explains that Strong/Remote are controlled by backend policy.
- When `/health` returns remote policy metadata, the UI shows the remote word limit and daily budget usage in the contextual note.

## Verification

- `python -m py_compile src/academic_engine/web/app.py`
- `node --check src/academic_engine/web/static/app.js`
- `python -m pytest tests/test_web_app.py -q`
  - Result: 11 passed.

## Notes

- No RunPod or DeepSeek calls were made.
- Policy storage is in-memory for the prototype. Production deployment should move counters/cache to Redis or another shared store if multiple backend processes are used.
