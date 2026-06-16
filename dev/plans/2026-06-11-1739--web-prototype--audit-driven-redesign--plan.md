# Web Prototype Audit-Driven Redesign Plan

Date: 2026-06-11

## Goal

Use `dev/audits/2026-06-11-1729--web-prototype-ui/audit.md` to turn the existing web prototype from a technical dashboard into a more polished guided academic diagnostic workspace.

## Scope

- Keep the existing FastAPI job API and detector/refinement behavior intact.
- Redesign the static web surface around public user intent:
  - detector-only diagnostic check
  - preservation-first refinement
- Hide or soften internal controls and raw provider details.
- Improve desktop and mobile result hierarchy.
- Verify with tests and a local browser pass if the server can run.

## Implementation Steps

1. Inspect current static UI and web tests.
2. Update `index.html` to support a guided workflow layout, user-facing presets, recommendation panel, and advanced detector disclosure.
3. Update `app.js` to:
   - map public presets to existing backend values
   - hide developer-only options from default UI
   - render recommendation-first detector/refinement results
   - keep raw detector rows in advanced details
4. Replace the visual layer in `styles.css` with a more intentional product UI:
   - compact header
   - segmented workflow control
   - document workspace + diagnostic rail
   - readable refined output
   - responsive mobile states
5. Run focused web/static tests.
6. Start or reuse the local server and inspect the app in the in-app browser.
7. Write a log and update `dev/index.md` if the redesign is important to rediscover.

## Out Of Scope

- Changing detector algorithms.
- Deploying or invoking RunPod/DeepSeek during UI work.
- Adding auth, accounts, storage, or production deployment.
