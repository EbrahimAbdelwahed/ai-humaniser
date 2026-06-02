# Decision: Use Detector Signals In Phase 1

## Status

Accepted.

## Context

The product mission is to help students reduce detector false positives while producing better academic writing. A CLI prototype that ignores detector signals would not validate whether prompt-based instructions are useful for the intended product.

The system must still preserve meaning, factual claims, terminology, citations, and argument structure.

## Decision

Include detector signal analysis in the Phase 1 CLI pipeline.

Detector signals may influence scoring, ranking, and refinement, provided hard preservation constraints remain gating criteria.

Use DeepSeek V4 Flash as the product runtime LLM:

```text
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Use environment variables for API keys and do not commit `.env` or private run artifacts.

## Consequences

- The CLI must include at least one local detector-risk heuristic so experiments work without external detector accounts.
- External detector integrations should use provider adapters and prefer official APIs or documented access methods.
- The engine may optimize for detector false-positive robustness, but must not claim guaranteed undetectability.
- Semantic preservation outranks detector score improvements.
