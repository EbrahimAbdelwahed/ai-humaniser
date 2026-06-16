# Web Prototype Audit-Driven Redesign Log

Date: 2026-06-11

## Summary

Redesigned the local Academic Engine web prototype using `dev/audits/2026-06-11-1729--web-prototype-ui/audit.md` as the guiding brief.

The UI now presents the product as a guided academic diagnostic workspace rather than an internal detector dashboard.

## Changed Files

- `src/academic_engine/web/static/index.html`
- `src/academic_engine/web/static/app.js`
- `src/academic_engine/web/static/styles.css`
- `dev/plans/2026-06-11-1739--web-prototype--audit-driven-redesign--plan.md`
- `dev/logs/2026-06-11-1739--web-prototype--audit-driven-redesign--log.md`
- `dev/index.md`

## Product Changes

- Replaced large card-style mode switch with a segmented workflow control.
- Reframed public modes as:
  - Detector check
  - Refine draft
- Added user-facing check profiles:
  - Quick: local signals
  - Strong: local + Fast-DetectGPT
  - Remote: Fast-DetectGPT only
- Moved raw preset/execution controls into `Advanced settings`.
- Removed the public `Use mock generation` control from the UI.
- Added a recommendation card above metrics and detector telemetry.
- Rendered detector output as:
  - recommendation
  - risk/confidence/signals metrics
  - plain-language meaning
  - optional advanced detector details
- Rendered refinement output as readable prose instead of a monospaced log block.
- Made the bottom information band contextual to mode and selected profile.
- Improved responsive behavior for mobile:
  - stacked workflow controls
  - stacked presets
  - reduced textarea height
  - no horizontal overflow in the verified mobile viewport

## Verification

- `node --check src/academic_engine/web/static/app.js`
- `python -m pytest tests/test_web_app.py -q`
  - Result: 8 passed.
- Browser verification at `http://127.0.0.1:8000/`:
  - initial redesigned DOM loaded
  - local Quick detector run succeeded from the UI
  - result showed recommendation-first summary
  - advanced detector details were collapsed by default
  - copy button enabled after successful run
  - mobile viewport `390x844` had no horizontal overflow
  - final browser console error log was empty

## Notes

- No RunPod or DeepSeek calls were intentionally made during this redesign pass.
- The local server was already running and reported Fast-DetectGPT as configured.
- Browser text entry required keypress fallback because the in-app browser virtual clipboard was unavailable.
