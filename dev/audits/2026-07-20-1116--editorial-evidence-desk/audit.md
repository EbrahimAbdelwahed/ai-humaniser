# Editorial Evidence Desk Design QA

Date: 2026-07-20

## Source of Truth

The selected direction is **Editorial Evidence Desk**: academic detector output is presented as a careful editorial margin note, not a machine verdict.

The composition, typography, palette, paper rules, folio markers, and restrained state feedback follow the source-of-truth brief in `dev/plans/2026-07-20-1116--web-prototype--editorial-evidence-desk--plan.md`.

## Evidence

- `desktop.png`: 1440 × 1000 initial viewport.
- `intermediate.png`: 1024 × 900 initial viewport.
- `mobile.png`: 390 × 844 initial viewport.
- `dense-result.png`: 1440 × 1000 completed Quick detector result.

## Findings and Fixes

- Fixed: the previous card-dashboard hierarchy was replaced by a document-and-evidence composition.
- Fixed: evidence tier and practical interpretation now dominate provider telemetry.
- Fixed: mobile initially delayed the document below the first viewport; the hero and workflow were compressed until the document begins at 580 px.
- Fixed: tabs now expose correct roving `tabindex`, arrow-key navigation, and selected state.
- Fixed: profile controls expose `aria-pressed`; copy feedback preserves its visible affordance.
- Verified: no horizontal overflow at 1440, 1024, or 390 px.
- Verified: detector result, profile selection, copy, advanced details, and keyboard tab switching work.
- Verified: reduced-motion rendering has no required ambient animation.
- Verified: primary-flow browser console contains no errors.

## Limitations

- The screenshots exercise the local Quick detector path. Remote Fast-DetectGPT was unavailable and no paid or external call was made.
- Visual contrast was reviewed in the rendered states, but no screen-reader session was performed.

## Result

**passed**
