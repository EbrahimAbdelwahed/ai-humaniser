# RunPod Flash Calibration Log

## Summary

Implemented an offline-safe RunPod Flash detector provider and a calibration audit path for teacher detectors.

## Changed Files

- `src/academic_engine/config.py`
- `src/academic_engine/detectors.py`
- `src/academic_engine/pipeline.py`
- `src/academic_engine/cli.py`
- `src/academic_engine/scoring.py`
- `scripts/runpod_flash/detectors_endpoint.py`
- `tests/test_cli.py`
- `tests/test_detector.py`
- `tests/test_pipeline_contract.py`
- `README.md`
- `.env.example`
- `pyproject.toml`

## Behavior

- Added detector sets: `flash`, `local+flash`, `community+flash`; `all` includes local, community, Flash, and HF.
- Added Flash config/env support:
  - `RUNPOD_API_KEY`
  - `ACADEMIC_ENGINE_FLASH_DETECTORS`
  - `ACADEMIC_ENGINE_FLASH_MODE`
  - shared and detector-specific Flash endpoint ids
  - Flash timeout seconds
- Flash provider returns standard `DetectorResult` objects.
- Missing `RUNPOD_API_KEY`, missing endpoint id, missing `runpod_flash`, bad output, or endpoint failure returns `available=false` with a clear error.
- Production mode keeps top-K teacher staging plus final-candidate audit.
- Calibration/research mode audits all generated candidates with teacher detectors.
- Added `academic-engine calibrate <input> -o <output> --detectors local+flash`, producing structured candidate audit artifacts.
- Flash scoring weights are stronger than local/community signals when available; hard preservation constraints remain gates.

## RunPod Flash Script

- Added `scripts/runpod_flash/detectors_endpoint.py`.
- Binoculars endpoint is implemented with imports inside the endpoint function and `workers=(0, 1)`.
- Ghostbuster, MAGE, and RADAR endpoints are explicit skeletons returning unavailable until their model/runtime setup is added.

## Verification

- `python -m pytest`: passed, 30 tests.
- `python -m academic_engine.cli calibrate examples/input/political_science.txt -o /private/tmp/academic-engine-flash-calibration-smoke.json --mock-provider --cycles 1 --detectors local+flash`: passed.
- Artifact smoke confirmed:
  - `artifact_type=academic_engine_calibration_audit`
  - `teacher_detector_policy=all_candidates`
  - `candidate_audits=7`
  - Flash detector entries are present and unavailable offline.
- `python -m academic_engine.cli --help`: passed.
- `python -c 'import runpod_flash; print("runpod_flash import ok")'`: passed after installing `runpod-flash`.
- `flash --help`: passed.
- `python -m py_compile scripts/runpod_flash/detectors_endpoint.py src/academic_engine/config.py src/academic_engine/detectors.py src/academic_engine/pipeline.py src/academic_engine/cli.py src/academic_engine/scoring.py`: passed.

## Notes

- No real GPU/RunPod detector call was made.
- `runpod-flash` was installed in the active Python environment for local verification.
- The generated `.flash/` CLI activity directory from `flash --help` was removed.
- Actual detector scoring requires deploying the Flash endpoint and configuring endpoint ids.

## Coordinator Review

- Fixed `detector_results(..., providers=[...])` so parallel execution checks the explicit provider subset, not the pipeline-wide detector list.
- Added a regression test for explicit-provider parallel execution.
- Added `.flash/` to `.gitignore` because the Flash CLI creates local activity metadata.
- Re-ran verification:
  - `python -m pytest`: passed, 31 tests.
  - `python -m academic_engine.cli calibrate examples/input/political_science.txt -o /private/tmp/academic-engine-flash-calibration-smoke.json --mock-provider --cycles 1 --detectors local+flash`: passed.
  - Import smoke for `scripts/runpod_flash/detectors_endpoint.py`: passed.
