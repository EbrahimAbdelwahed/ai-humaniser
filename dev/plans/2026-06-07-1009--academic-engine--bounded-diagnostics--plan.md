# Bounded Diagnostics Plan

## Objective

Add an offline-safe diagnostic refinement module under `src/academic_engine/` that converts score cards, detector results, and text context into serializable failure modes and bounded rewrite guidance.

## Scope

- Add a new module only; do not edit `pipeline.py`, `cli.py`, `scoring.py`, or `config.py`.
- Add focused deterministic tests.
- Preserve existing detector semantics and treat detector signals as diagnostics, not verdicts.

## Steps

1. Inspect existing schemas and scoring diagnostics.
2. Implement public coordinator-facing functions/classes for diagnostic extraction and rewrite planning.
3. Cover official Fast-DetectGPT elevated signals, confidence, and baseline deltas.
4. Cover stylometric modes for specificity, repetition, transitions, sentence rhythm, and generic LLM pattern risk.
5. Run focused tests and write a completion log.
