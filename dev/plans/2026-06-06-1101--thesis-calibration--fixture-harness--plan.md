# Thesis Calibration Fixture Harness Plan

## Scope

Prepare local-only thesis calibration fixtures and baseline raw-audit artifacts under `experiments/thesis_calibration_2026_06_06/`.

## Steps

1. Inspect existing raw-audit artifact shape and CLI usage.
2. Extract DOCX text locally and normalize all three provided inputs into `.txt` fixture copies.
3. Create a manifest with labels, source types, word counts, and content hashes.
4. Run `raw-audit` with `--detectors local` and save the baseline artifact.
5. Run focused verification without network/API/GPU calls.

## Constraints

- Do not modify detector source code.
- Do not overwrite original input files.
- Avoid network/API/GPU calls.
