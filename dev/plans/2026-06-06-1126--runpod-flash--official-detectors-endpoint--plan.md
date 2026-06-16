# Official Detectors Flash Endpoint Plan

## Goal

Add a cost-aware RunPod Flash endpoint for official detector runtimes without deploying or calling RunPod.

## Scope

- Add `scripts/runpod_flash/official_detectors_endpoint.py`.
- Support batch-friendly scoring for `official_binoculars` and `official_fast_detectgpt`.
- Return explicit unavailable/failure-mode payloads for missing dependencies, model repos, empty text, bad payloads, timeouts, and wrapper failures.
- Document that Ghostbuster official requires `OPENAI_API_KEY` and is not executed unless present.
- Keep default GPU config at 24GB (`ADA_24`/`AMPERE_24`), `workers=(0, 1)`, and a short idle timeout.
- Add focused tests if feasible.

## Verification

- Compile the new endpoint.
- Run focused tests for wrapper help and endpoint helper behavior.
