# Decision: Use Local Markdown Memory

## Status

Accepted.

## Context

Future agents need a lightweight way to recover project context without relying on chat history.

## Decision

Use `dev/` as the repository-local Markdown memory store.

Supported record types:

- plans
- logs
- notes
- decisions
- handoffs

All memory files use:

```text
YYYY-MM-DD-HHMM--area--task--type.md
```

`dev/index.md` remains curated and links only important references.

## Consequences

- Agents must read `AGENTS.md`, read `dev/index.md`, and search `dev/` before intervening.
- Complex work should have a plan before implementation.
- Meaningful work should leave a factual log after completion.
- The system stays simple and works without external services.
