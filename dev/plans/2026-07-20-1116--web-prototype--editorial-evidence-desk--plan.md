# Editorial Evidence Desk UI Plan

## Brief

- Audience: students, researchers, and supervisors reviewing academic prose.
- Primary task: paste a passage, choose an evidence profile, and understand the result or refinement without reading detector telemetry.
- Required interactions: workflow switch, profile selection, text entry, analysis/refinement, copy output, advanced settings and detector disclosure.
- Visual thesis: an academic evidence desk that treats detector output like a careful editorial margin note, not a machine verdict.
- Constraints: preserve the current FastAPI and JavaScript contracts, truthful evidence-tier language, keyboard access, reduced motion, and responsive layouts.
- Success: the first viewport exposes the task and evidence boundary immediately; results are legible at 1440, 1024, and 390 pixels with no lost controls or accidental overflow.

## Source of Truth

Direction: **Editorial Evidence Desk**.

- Composition: slim publication masthead, dominant document desk, narrower evidence folio, and a ruled provenance footer.
- Typography: Georgia-style editorial display and prose; system sans-serif for controls and metadata; monospace only for raw provider identifiers.
- Palette: warm paper, carbon ink, bottle green as the functional color, and restrained vermilion for warnings.
- Material: paper rules, margin annotations, folio numbering, and evidence markers derived from academic review.
- Motion: short state transitions and progress feedback only; all nonessential motion disabled by `prefers-reduced-motion`.

## Implementation

1. Capture the current rendered interface and important interaction state.
2. Recompose the HTML while preserving all JavaScript selectors and behaviors.
3. Replace the visual system and responsive rules around the editorial thesis.
4. Improve state feedback, tab semantics, copy feedback, and mobile navigation behavior.
5. Run static checks and focused web tests.
6. Capture desktop, intermediate, mobile, and dense-result screenshots; fix visual defects.
7. Record design QA evidence and the final result in `dev/logs/`.
