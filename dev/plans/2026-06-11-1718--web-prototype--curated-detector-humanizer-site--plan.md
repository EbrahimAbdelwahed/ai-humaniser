# Web Prototype Curated Detector Humanizer Plan

## Goal

Turn the existing web MVP into a more polished prototype for two workflows:

- detector-only diagnostics on pasted academic text
- bounded text refinement with preservation reporting

The backend must expose Fast-DetectGPT on demand through the existing official RunPod routing when an endpoint is configured, while remaining usable with local detectors when it is not.

## Constraints

- Do not claim guaranteed detector outcomes.
- Keep detector results diagnostic and expose unavailable remote signals clearly.
- Avoid adding paid RunPod work during UI/backend implementation unless explicitly needed for smoke testing.
- Preserve existing pipeline/refinement logic rather than duplicating detector behavior in the web layer.

## Implementation Steps

1. Backend web contract
   - Keep presets focused: `local`, `local+fast-detectgpt`, `official-fast-detectgpt`.
   - Report Fast-DetectGPT readiness in `/health`, including endpoint configuration status.
   - Make `local+fast-detectgpt` include only local detectors plus official Fast-DetectGPT, not Binoculars or Ghostbuster.
   - Surface provider availability and warnings in compact web DTOs.

2. Frontend redesign
   - Replace the MVP panel layout with a more refined product-tool interface.
   - Provide clear mode switching, detector preset selection, text limits, queued/running/success states, and copyable refined output.
   - Present risk, disagreement, availability, and detector details without dumping raw JSON by default.
   - Keep mobile layout stable and dense enough for repeated testing.

3. Verification
   - Add or update web tests for health metadata, focused Fast preset routing, and summary shape.
   - Run web tests and then the full suite if feasible.
   - Start the local web server and verify the UI with the in-app browser.

4. Follow-up boundary
   - Live Fast-DetectGPT scoring requires `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` and `RUNPOD_API_KEY`.
   - If the endpoint is not configured, the site must say so instead of silently implying Fast-DetectGPT ran.
