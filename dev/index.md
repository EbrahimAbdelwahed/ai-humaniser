# Development Memory Index

Curated references only.

## Process

- [Local memory protocol](../AGENTS.md): required startup and Markdown memory rules.
- [Memory directory guide](README.md): directory purposes, naming, and index policy.

## Decisions

- [Use local Markdown memory](decisions/2026-06-02-1202--dev-memory--markdown-memory--decision.md): establishes `dev/` as the durable local memory system.
- [Use detector signals in Phase 1](decisions/2026-06-02-1206--academic-engine--detector-signal-runtime--decision.md): detector-risk signals are part of the CLI loop, while semantic preservation remains the hard gate.

## Current State

- [Initial memory setup handoff](handoffs/2026-06-02-1202--dev-memory--initial-setup--handoff.md): current status after bootstrapping the system.
- [Worker-ready academic engine architecture](plans/2026-06-02-1205--academic-engine--worker-ready-architecture--plan.md): Phase 1 plan and launch contract for a `gpt-5.5` worker with low reasoning effort.
- [Academic engine worker handoff](handoffs/2026-06-02-1206--academic-engine--worker-ready--handoff.md): current requirements and worker launch state after detector/DeepSeek clarifications.
