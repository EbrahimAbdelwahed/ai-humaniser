# Web Prototype Remote Endpoint Policy Plan

Date: 2026-06-11

## Goal

Implement backend-side controls for using the Fast-DetectGPT/RunPod endpoint from the web app.

## Scope

- Browser continues to call only the FastAPI backend.
- Remote detector usage is controlled by backend policy.
- Add cache and rate-limit behavior around remote detector providers.
- Degrade to local detectors with explicit warnings when policy blocks remote usage.
- Expose policy status in `/health`.
- Keep tests offline-safe; do not call RunPod or DeepSeek.

## Steps

1. Add web settings for remote detector policy:
   - enable flag
   - remote max words
   - global daily limit
   - per-client daily limit
   - minimum interval per client
   - cache TTL
2. Add in-memory policy state:
   - per-client counters
   - global counter
   - detector-result cache keyed by normalized text + provider + route config
3. Wrap remote detector providers so web requests use cache and policy checks before any external call.
4. Apply fallback-to-local behavior when remote is disabled, over word limit, rate-limited, or not configured.
5. Add warnings and remote usage metadata to detection/refinement payloads.
6. Add tests for health metadata, downgrade behavior, cache hit behavior, and rate-limit behavior.
7. Run focused tests and compile checks.

## Out Of Scope

- Persistent database-backed rate limiting.
- User authentication/account quotas.
- RunPod deploys or live endpoint calls.
- Frontend copy changes beyond consuming existing warning fields if needed.
