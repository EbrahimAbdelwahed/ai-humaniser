# Web Prototype UI Audit Plan

## Scope

Audit the current local web prototype UI for:

- Initial screen and visual positioning.
- Detector-only workflow.
- Refinement workflow setup state.
- Result presentation after a detector run.

## Destination

Save output locally under:

`dev/audits/2026-06-11-1729--web-prototype-ui/`

## Method

1. Use the in-app Browser on the current local app when available.
2. Capture screenshots for each relevant state.
3. Inspect saved screenshots before accepting them as evidence.
4. Write a concise combined UX, visual design, and accessibility audit tied to the captured steps.
5. Log the audit output and index it if useful for future redesign work.

## Constraints

- Do not edit the UI during the audit.
- Do not run live GPU detector calls unless already needed by a visible state; local/mock interactions are sufficient for UI evidence.
- Do not claim WCAG compliance from screenshots alone.
