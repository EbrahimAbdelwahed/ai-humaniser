# Direct RunPod Fast-DetectGPT Plan

## Goal

Make the web Fast-DetectGPT preset call the configured RunPod Flash endpoint directly from the Python process instead of routing through a subprocess CLI wrapper.

## Steps

1. Add an official RunPod Flash detector provider that uses `runpod_flash.Endpoint(id=...).runsync(...)`.
2. Route `official_fast_detectgpt` to that provider when `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` is configured.
3. Preserve the existing CLI provider fallback when no endpoint id is configured.
4. Add or update tests for provider selection and unavailable error handling.
5. Run focused tests and log the work.

