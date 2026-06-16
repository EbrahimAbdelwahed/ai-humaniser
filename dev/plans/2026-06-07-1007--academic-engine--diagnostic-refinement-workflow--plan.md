# Diagnostic Refinement Workflow Plan

## Objective

Implement a refinement workflow that uses detector and stylometric failure modes as diagnostics to guide bounded academic rewrites. Fast-DetectGPT remains the primary model-based artificiality-risk signal, but the loop must optimize for preservation, naturalness, specificity, and non-disruptive edits rather than detector-score reduction alone.

## Constraints

- Do not frame the implementation as detector evasion.
- Preserve citations, numeric values, terminology, factual claims, and argument structure as hard gates.
- Keep RunPod optional and cost-controlled; local/mock verification must work without billable resources.
- Use DeepSeek through the existing provider path for live generation when configured.
- Save rejected candidates and their failure modes for later distillation.
- Keep the workflow modular for a future web app.

## Implementation Phases

1. Add diagnostic extraction.
   - Create a module that maps `ScoreCard`, `DetectorResult`, text statistics, and hard-gate failures into explicit failure modes and rewrite recommendations.
   - Include detector-specific interpretation for `official_fast_detectgpt`, especially elevated risk, high confidence, and score deltas.
   - Include stylometric modes: uniform rhythm, low specificity, repetition, generic phrasing, formulaic transitions, weak sentence-length variance.

2. Add strategy planning.
   - Convert failure modes into a structured rewrite plan.
   - Include change budget, preservation constraints, target interventions, and avoid-list.
   - The plan must be serializable for artifacts and prompt construction.

3. Wire diagnostics into refinement.
   - Before each refinement cycle, extract failure modes from the current candidate.
   - Build a refinement prompt that includes the rewrite plan, preservation constraints, and detector diagnostics.
   - Generate one candidate per cycle, then rescore with the existing detector providers.
   - Accept only if preservation gates pass and composite utility improves or if detector risk drops without disruptive change.

4. Add artifacts and CLI surface.
   - Add a `refine-diagnostics` command or extend current `run` output with diagnostic summaries.
   - Ensure final reports include accepted/rejected diagnostic plans and before/after detector deltas.
   - Preserve existing CLI behavior.

5. Verify locally first.
   - Add unit tests for failure-mode extraction and strategy planning.
   - Add pipeline contract tests using deterministic mock detector providers.
   - Run mock workflow against thesis calibration snippets if available locally.

6. Optional live verification.
   - If RunPod and DeepSeek are configured and explicitly useful after local tests, run a small live pass with official Fast-DetectGPT only.
   - Undeploy immediately after live detector checks.

## Worker Split

- Worker low reasoning: implement diagnostic extraction and planning module plus focused tests.
- Coordinator: integrate the module into `AcademicRewritePipeline`, update schemas/CLI/artifacts, run verification, and write memory log.

## Success Criteria

- The pipeline emits clear failure modes for high-risk candidates.
- Refinement prompts are guided by those failure modes.
- Rejected candidates retain failure-mode and hard-gate audit data.
- Mock verification demonstrates at least one refinement iteration improves composite utility without hard-gate failures.
- Existing tests continue passing.
