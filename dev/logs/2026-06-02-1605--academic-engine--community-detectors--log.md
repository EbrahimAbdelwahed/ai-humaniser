# Community Detector Integration Log

## Summary

Implemented optional community detector adapters for Binoculars, Ghostbuster, MAGE, and RADAR as local-model detector signals.

## Changed Files

- `src/academic_engine/detectors.py`
- `src/academic_engine/scoring.py`
- `src/academic_engine/config.py`
- `src/academic_engine/cli.py`
- `src/academic_engine/pipeline.py`
- `tests/test_detector.py`
- `tests/test_scoring.py`
- `tests/test_pipeline_contract.py`
- `README.md`
- `.env.example`
- `dev/plans/2026-06-02-1605--academic-engine--community-detectors--plan.md`
- `dev/logs/2026-06-02-1605--academic-engine--community-detectors--log.md`
- `dev/index.md`

## Implementation Notes

- Added detector sets: `community`, `local+community`, and `all`, while keeping `local` as the default.
- Added lazy `community_binoculars` provider that imports official `ahans30/Binoculars` only when selected. It also supports `ACADEMIC_ENGINE_BINOCULARS_CLI`.
- Added CLI-wrapper adapters for `community_ghostbuster`, `community_mage`, and `community_radar`.
- Wrapper commands read text from stdin and return either a numeric score or JSON with `score`/`confidence`/`label`.
- Community providers return standard `DetectorResult` objects with `provider_kind=local_model`.
- Missing dependencies, missing model assets, or missing wrapper commands return `available=false` and do not break the pipeline.
- Added optional detector execution mode config: sequential default, parallel opt-in capped at concurrency `2`.
- Updated consensus weights so available community detectors outweigh lightweight heuristic signals.
- Updated final report detector analysis with execution mode, community provider list, available community providers, and unavailable detector errors.

## Verification

- `python -m pytest`: passed, 23 tests.
- `python -m academic_engine.cli run examples/input/political_science.txt -o /private/tmp/academic-engine-community-smoke.json --mock-provider --cycles 1 --detectors local+community`: passed.
  - final detector risk: `0.1839`
  - consensus: `lower_risk`
  - community providers present: Binoculars, Ghostbuster, MAGE, RADAR
  - available community providers: none
  - unavailable detector count: `4`
- `python -m academic_engine.cli run examples/input/political_science.txt -o /private/tmp/academic-engine-community-only-smoke.json --mock-provider --cycles 1 --detectors community`: passed.
  - detector consensus: `unavailable`
  - unavailable detector count: `4`
- Forced-cycle mock with `local+community`: passed.
  - cycles: `1`
  - stop reason: `max_refinement_cycles_reached`
  - unavailable detector count: `4`

## Download / Install Attempt

Attempted temporary Binoculars install:

```sh
python -m pip install --target /private/tmp/academic-engine-binoculars-smoke git+https://github.com/ahans30/Binoculars.git
```

The first attempt failed in the sandbox with DNS resolution blocked. The escalated attempt downloaded the official repo and dependencies, including Torch and Transformers, but failed building `tokenizers 0.13.3` from source on Python `3.13.12` due a Rust compile error. No live Binoculars model smoke was completed.

Practical next install path:

- Use Python `3.10` or `3.11` for community detector environments so `tokenizers`/Transformers wheels are available.
- Install Binoculars in a separate local environment, cache models, then either use direct import or set `ACADEMIC_ENGINE_BINOCULARS_CLI`.
- For Ghostbuster, MAGE, and RADAR, install official repos/resources separately and expose local stdin-to-JSON wrapper commands through the corresponding `ACADEMIC_ENGINE_*_CLI` variables.

## Current Detector Status

- Working in repo: local heuristic ensemble.
- Working as adapter/fallback: Binoculars, Ghostbuster, MAGE, RADAR, HuggingFace detector.
- Not live-verified: Binoculars, Ghostbuster, MAGE, RADAR due missing local installs/model assets.
