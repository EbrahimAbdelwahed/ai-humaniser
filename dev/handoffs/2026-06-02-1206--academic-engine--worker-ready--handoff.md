# Handoff: Academic Engine Worker Ready

## State

The architecture for Phase 1 is ready for a worker to implement.

The latest source of truth is:

- `dev/plans/2026-06-02-1205--academic-engine--worker-ready-architecture--plan.md`
- `dev/decisions/2026-06-02-1206--academic-engine--detector-signal-runtime--decision.md`

## Important Requirements

- Final product direction is a web app, but Phase 1 is CLI-first.
- Product runtime LLM is DeepSeek API model `deepseek-v4-flash`.
- The implementation worker can be launched as `agent_type=worker`, `model=gpt-5.5`, `reasoning_effort=low`.
- Detector signals are part of the Phase 1 CLI scoring, ranking, and refinement loop.
- Semantic preservation, factual preservation, citation preservation, and non-disruptive edits remain hard gates.
- User-provided citations should be preserved exactly; no citation-style normalization in Phase 1.
- `.env` and private manuscript/run artifacts should not be publicly exposed or committed.

## Worker Launch

Use the launch prompt embedded in the architecture plan.

## Open Items

- Actual external detector integrations depend on usable API keys or acceptable access paths.
- Detector-risk targets for early experiments still need empirical tuning.
- Web app backend stack can be decided after the CLI engine proves useful.
