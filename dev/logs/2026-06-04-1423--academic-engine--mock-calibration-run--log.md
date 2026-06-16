# Mock Calibration Run

Ran offline/mock calibration to evaluate the candidate audit pipeline without external API calls or RunPod GPU cost.

## Commands

```sh
python -m academic_engine.cli calibrate examples/input/political_science.txt -o examples/output/political_science.mock-calibration.local.json --mock-provider --cycles 2 --detectors local --detector-execution sequential
```

```sh
python -c 'from dataclasses import replace; from pathlib import Path; from academic_engine.config import EngineConfig; from academic_engine.pipeline import AcademicRewritePipeline; config=EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=2, detector_set="local+flash"); config=replace(config, runpod_api_key=None, flash_endpoint_id=None, flash_endpoint_ids={}, flash_mode="calibration"); AcademicRewritePipeline(config=config).calibration_audit(Path("examples/input/political_science.txt"), Path("examples/output/political_science.mock-calibration.local-flash-offline.json"))'
```

The second command forces RunPod credentials and endpoint ids to `None` in memory before provider construction, so it exercises Flash-unavailable audit behavior without permitting a GPU/API call.

## Results

- Local-only artifact: `examples/output/political_science.mock-calibration.local.json`
- Local+Flash-offline artifact: `examples/output/political_science.mock-calibration.local-flash-offline.json`
- Input: `examples/input/political_science.txt`
- Candidate audits per run: 7
- Selected candidate in both runs: `candidate-6`, strategy `non_native_refinement`
- Selected utility: `0.8352`
- Selected weighted quality: `0.8336`
- Selected detector risk: `0.2417`
- Selected detector consensus: `lower_risk`
- Selected detector disagreement: `0.3964`

Local detector availability:

- `local_stylometry_burstiness`: 7/7 available
- `local_lexical_diversity`: 7/7 available
- `local_gltr_lite_probability_shape`: 7/7 available
- `local_repetition_genericity`: 7/7 available
- `local_readability_academic_pattern`: 7/7 available
- `local_heuristic_detector_risk`: 7/7 available

Flash-offline audit behavior:

- `flash_roberta_cluster`: 0/7 available
- Excluded candidates recorded `detector_unavailable` and `runpod_unavailable` failure modes.
- Winner did not receive exclusion failure modes because it is not excluded.

## Verification

```sh
python -m pytest tests/test_pipeline_contract.py tests/test_schemas.py
```

Passed: 15 tests.

## Observations

- The calibration artifact is structurally useful: it records all candidates, ranks, detector scores, preservation quality, exclusion reasons, and failure modes.
- The political-science sample is too short and easy for meaningful refinement stress testing. All local-only candidates pass hard gates, so exclusions are rank-based rather than quality/fidelity failures.
- Local detector disagreement is high enough to be surfaced as a caveat, which is correct for heuristic-only scoring.
- The next useful offline evaluation should use longer fixture texts and a stricter/custom calibration run that forces semantic, citation, or numeric drift cases so failure modes become more informative.
