# Web Prototype UI Audit

Date: 2026-06-11

## Scope

Combined UX, visual design, and accessibility audit for the local Academic Engine web prototype at `http://127.0.0.1:8000/`.

Captured flow:

1. Initial detector screen.
2. Detector screen with text entered.
3. Detector result screen after a local detector run.
4. Humanizer setup screen.
5. Humanizer result screen after a mock refinement run.
6. Mobile viewport of the humanizer result flow.

Screenshots are saved in `screenshots/`.

## Step List

1. Initial detector screen
   General health: functional but visually too close to an internal admin tool. The page is clear, but it does not yet create product confidence.

2. Detector text entry
   General health: usable. The input is easy to find, but the control area feels like a raw form instead of a guided analysis workflow.

3. Detector results
   General health: moderately useful. The user gets concrete metrics, but the presentation exposes implementation names and does not translate findings into next actions.

4. Humanizer setup
   General health: functional but too technical for public testing. `Use mock generation` and `Refinement cycles` expose prototype internals.

5. Humanizer mock results
   General health: the before/after idea is right. The screen needs stronger hierarchy, better explanation of why a result was accepted, and a more readable output comparison.

6. Mobile viewport
   General health: responsive basics work, but the page becomes a long stacked form with limited product polish and weak progress/navigation support.

## Strengths

- The two core modes are visible immediately: detector and humanizer.
- The product correctly says that detector results are diagnostic, not verdicts.
- Status pills communicate backend and Fast-DetectGPT readiness.
- The two-column desktop layout works for a power-user workflow: input on the left, output on the right.
- Result cards for risk, disagreement, and unavailable detectors are scannable.
- Preservation and warning sections are present, which supports trust if improved.

## UX Risks

1. The UI still reads as a prototype dashboard, not a product.

   Evidence: `01-initial-detector-empty.png` and `03-detector-results.png`.

   The structure is tidy but generic: logo block, two cards, textarea, selects, output panel. There is little sense of an opinionated workflow, no visual narrative, no meaningful onboarding, and no confidence-building affordances beyond short copy.

2. The mode switch looks like two large cards, but behaves like tabs.

   Evidence: `01-initial-detector-empty.png` and `04-humanizer-mode.png`.

   This makes the first interaction slightly ambiguous. A segmented workflow header, with active state and task-specific description, would be clearer.

3. Controls expose implementation details.

   Evidence: `04-humanizer-mode.png`.

   `Use mock generation` should not appear in a public prototype. `Sequential` / `Parallel` and raw detector presets may be useful internally, but they make the app feel unfinished. Public-facing wording should map to user intent, such as `Quick local check`, `Deep detector check`, and `Cost-aware remote check`.

4. The result report lacks a clear recommendation layer.

   Evidence: `03-detector-results.png` and `05-humanizer-mock-results.png`.

   The metrics are present, but the screen does not clearly answer: "What does this mean?" or "What should I change next?" The warning is correct but generic. Detector rows are mostly provider telemetry.

5. Detector names dominate the wrong level of hierarchy.

   Evidence: `03-detector-results.png`.

   Names like `local_gltr_lite_probability_shape` and `local_readability_academic_pattern` are useful for debugging, but they should be collapsed under advanced details. The default report should emphasize risk bands, confidence, disagreement, and writing-level failure modes.

6. The refined text area is visually secondary and hard to compare.

   Evidence: `05-humanizer-mock-results.png`.

   The output is shown in a monospaced block inside the result rail. That makes it feel like a log artifact, not the main deliverable. Users need a strong output surface with copy/download controls and a before/after or diff-oriented view.

7. The bottom information band is useful but static and generic.

   Evidence: all desktop screenshots.

   It repeats three educational notes but does not react to the chosen mode, selected detector preset, or result warning. This is space that could explain the current run and privacy/cost implications contextually.

8. Mobile is usable but not designed as a mobile product.

   Evidence: `06-mobile-humanizer-results.png`.

   The content stacks correctly, but the input consumes most of the first viewport after the header. There is no sticky action, no compressed summary, and no quick path from result back to text. The user has to scroll through a long operational form.

## Accessibility Risks

1. Focus state is visible but visually inconsistent.

   Evidence: `04-humanizer-mode.png`.

   The active Humanizer card shows a strong ring that reads like keyboard focus or validation, not necessarily selected mode. Active, hover, and keyboard focus states should be visually distinct.

2. Status pills may not be announced as live status.

   Evidence: `01-initial-detector-empty.png`.

   From screenshots and DOM, they appear as generic text. The backend/Fast readiness state should be programmatically associated with status semantics if it changes after load.

3. Metric meaning depends on color and terse labels.

   Evidence: `03-detector-results.png`.

   `lower risk`, `moderate risk`, and tiny `available` chips are text-backed, which helps, but users still need clearer explanatory text for risk bands. Screenshot-only audit cannot confirm color contrast values.

4. Checkbox and advanced controls may be small on mobile.

   Evidence: `06-mobile-humanizer-results.png`.

   The checkbox itself is small and the label is technical. It should become a full-width setting row or be removed from public mode.

5. Long detector names and monospaced refined text may create reading burden.

   Evidence: `03-detector-results.png` and `05-humanizer-mock-results.png`.

   Screen-reader output could be noisy if every detector row is announced as raw provider names. Visual users also get a debug-log feeling.

## Priority Recommendations

1. Redesign the top-level experience around an analysis workflow, not a form.

   Suggested structure:

   - Left: document workspace with textarea/upload, word count, citation-preservation reminder.
   - Right: diagnostic summary with risk band, confidence, action recommendation, and run cost/speed.
   - Below or drawer: advanced detector details.

2. Replace internal options with user-facing presets.

   Current:

   - `Local ensemble`
   - `Local + Fast-DetectGPT`
   - `Fast-DetectGPT only`
   - `Sequential`
   - `Parallel`
   - `Use mock generation`

   Better public mode:

   - `Quick check`
   - `Strong check`
   - `Remote Fast-DetectGPT`
   - hide execution mode behind developer settings
   - remove mock generation from public UI

3. Add a recommendation card above raw metrics.

   Example information:

   - `Current risk: lower`
   - `Confidence: mixed because local signals disagree`
   - `Main issue: sentence rhythm is uniform`
   - `Recommended next action: revise sentence variety, keep citations unchanged`

4. Make the humanizer output the hero of the completed state.

   Use a larger output panel with:

   - refined text as normal prose, not monospace
   - copy button near the output title
   - before/after score delta
   - accepted/rejected candidate explanation
   - optional diff view

5. Collapse detector providers into an advanced disclosure.

   Default result should show:

   - aggregate risk
   - disagreement
   - available/unavailable detector count
   - top failure modes

   Raw provider rows should live under `Advanced detector details`.

6. Improve visual identity.

   The current system is clean but flat. Add a more intentional product layer:

   - stronger page rhythm and section boundaries
   - smaller but sharper header
   - clearer active mode styling
   - better button hierarchy
   - fewer bordered containers competing for attention
   - a more polished result summary treatment

7. Improve mobile flow.

   - Put mode switch and primary action in compact sticky controls.
   - Let users collapse the input after a result is produced.
   - Show the result summary before the full detector stack.
   - Avoid making the textarea dominate the mobile viewport.

## Evidence Limits

- This audit is screenshot- and DOM-observation based. It does not prove full keyboard accessibility, screen-reader quality, or contrast compliance.
- The detector result used local signals only. Fast-DetectGPT remote states, loading duration, timeout handling, and failure states were not captured.
- The humanizer result used mock generation to avoid external model calls during the audit.
- No production analytics or real user behavior were available.

## Suggested Next Design Pass

The UI should move from "developer console for a text engine" to "guided academic diagnostic workspace." The current foundation is acceptable for internal validation, but for external feedback it needs:

1. Less exposed machinery.
2. More guidance and interpretation.
3. A stronger completed-result state.
4. A cleaner mobile path.
5. A visibly intentional product identity.
