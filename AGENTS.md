# AGENTS.md

## Local Memory Protocol

Before changing this repository, an agent must:

1. Read this file.
2. Read `dev/index.md` if it exists.
3. Search `dev/` for relevant plans, logs, notes, decisions, and handoffs before intervening.

Use local Markdown memory under `dev/` for work that should be discoverable across sessions.

## Memory Types

- `plans`: create before complex or multi-step work.
- `logs`: write after meaningful work, including verification and changed files.
- `notes`: capture reusable project knowledge.
- `decisions`: record stable ADR-style decisions.
- `handoffs`: preserve current state for the next session.

## File Rules

- Keep files small, factual, and scoped to one topic.
- Use this naming format:

```text
YYYY-MM-DD-HHMM--area--task--type.md
```

- Use lowercase `area`, `task`, and `type`.
- Prefer short slugs separated by hyphens.
- Do not put every memory file in `dev/index.md`; only add entries that are important to rediscover.

## Workflow

Before complex work:

1. Search existing memory:

```sh
rg -n "keyword|area|task" dev
```

2. Create a plan in `dev/plans/`.

After work:

1. Write a log in `dev/logs/`.
2. Add reusable knowledge to `dev/notes/` only when it is likely to matter again.
3. Add a decision in `dev/decisions/` only for stable architectural or process decisions.
4. Add or update a handoff in `dev/handoffs/` when the next session needs state.
5. Update `dev/index.md` only for important references.
