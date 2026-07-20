# Editorial Evidence Desk UI Log

Date: 2026-07-20

## Summary

Implemented the selected Editorial Evidence Desk direction for the Academic Engine web interface while preserving the existing detector and refinement contracts.

## Changed Files

- `src/academic_engine/web/static/index.html`
- `src/academic_engine/web/static/styles.css`
- `src/academic_engine/web/static/app.js`
- `dev/plans/2026-07-20-1116--web-prototype--editorial-evidence-desk--plan.md`
- `dev/audits/2026-07-20-1116--editorial-evidence-desk/`
- `dev/logs/2026-07-20-1116--web-prototype--editorial-evidence-desk--log.md`

## Product Changes

- Introduced a publication masthead, editorial hero, ruled manuscript editor, numbered folios, and margin-note result treatment.
- Replaced interchangeable card styling with a document/evidence hierarchy.
- Kept Quick, Strong, and Remote profiles plus advanced detector settings.
- Improved tab semantics, arrow-key navigation, profile pressed states, copy feedback, visible focus, and reduced-motion handling.
- Reworked responsive composition so mobile reaches the document workspace in the first viewport.

## Verification

- `node --check src/academic_engine/web/static/app.js`
- `PYTHONPATH=src python -m pytest -q`: 107 passed.
- Rendered QA at 1440 × 1000, 1024 × 900, and 390 × 844.
- Dense local detector result rendered successfully with the copy action enabled.
- No horizontal overflow or primary-flow browser console errors.
- Keyboard workflow switch, profile selection, copy, and advanced disclosure verified.

## External Boundaries

No remote detector, model, deployment, or billable service was called.
