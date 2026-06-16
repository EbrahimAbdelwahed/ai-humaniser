# Community Detector Integration Plan

## Goal

Add optional local/community detector providers for Binoculars, Ghostbuster, MAGE, and RADAR as stronger signals in scoring and refinement while preserving hard gates on citations, numbers, facts, claims, terminology, and argument structure.

## Scope

- Inspect existing detector provider selection, scoring consensus, CLI reporting, and tests.
- Add lazy provider adapters that return standard `DetectorResult` objects and degrade to `available=false` when dependencies, repos, models, or commands are missing.
- Add detector-set choices: `local`, `local+hf`, `community`, `local+community`, and `all`.
- Keep sequential execution as the default. Add config flags for optional parallelism/concurrency only if it can be implemented conservatively.
- Weight available community detector signals more strongly than lightweight heuristics and report disagreement/unavailable notes.
- Add tests for selection, fallback behavior, consensus weighting, and pipeline resilience.
- Attempt practical install/smoke for Binoculars or another community detector if the sandbox permits downloads.

## Verification

- `python -m pytest`
- CLI mock run with `--detectors local+community`
- CLI community-only smoke on a short sample
- Document any blocked downloads/install steps and required commands.
