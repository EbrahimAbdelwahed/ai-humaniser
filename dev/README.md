# Local Development Memory

This directory stores small Markdown records that help future agents recover context.

## Required Startup

Before intervening in the repository:

1. Read `AGENTS.md`.
2. Read `dev/index.md`.
3. Search the rest of `dev/` for relevant context.

## Directories

- `plans/`: intended approach before complex work.
- `logs/`: completed work, verification, and changed files.
- `notes/`: reusable facts and project knowledge.
- `decisions/`: stable ADR-style records.
- `handoffs/`: state for continuing later.

## Naming

Use:

```text
YYYY-MM-DD-HHMM--area--task--type.md
```

Example:

```text
2026-06-02-1202--dev-memory--initial-setup--plan.md
```

## Index Policy

`index.md` is curated. Add only references that future agents should actively rediscover.
