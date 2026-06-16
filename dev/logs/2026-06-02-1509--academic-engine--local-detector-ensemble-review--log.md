# Local Detector Ensemble Review Log

## Summary

Reviewed the worker implementation of the local detector ensemble and made one coordinator follow-up fix so detector-set selection and final candidate selection behave consistently.

## Follow-Up Changes

- Made `--detectors hf` use only the optional HuggingFace detector provider.
- Kept `--detectors local` as the lightweight local ensemble.
- Kept `--detectors local+hf` as local ensemble plus optional HuggingFace detector.
- Adjusted final safe-candidate selection to prefer lower detector risk when candidate utilities are practically tied.
- Added regression tests for detector-set selection and close-utility detector-risk preference.

## Verification

```sh
python -m pytest
python -m academic_engine.cli run examples/input/political_science.txt -o examples/output/political_science.result.json --mock-provider --cycles 1 --detectors local
python -m academic_engine.cli run examples/input/political_science.txt -o examples/output/political_science.hf-unavailable.result.json --mock-provider --cycles 1 --detectors local+hf
python -m academic_engine.cli run examples/input/political_science.txt -o examples/output/political_science.hf-only.result.json --mock-provider --cycles 1 --detectors hf
python -m academic_engine.cli experiment tests/fixtures -o examples/output/experiment-summary.json --mock-provider --cycles 1 --detectors local
```

Results:

- pytest: `17 passed`
- local CLI smoke: passed
- local+HF CLI smoke: passed, HF unavailable was recorded without breaking the run
- HF-only CLI smoke: passed, no available detector signals because `transformers` is not installed locally
- experiment: `fixture_count=4`, average detector risk moved from `0.2449` before to `0.1986` after, with no hard constraint failures

## Notes

- Forced-cycle mock with strict thresholds ran one refinement cycle. The refinement slightly worsened local detector risk, so final selection preferred a safer ranked candidate with lower detector risk.
- Local detector scores remain uncalibrated diagnostic signals. Mainstream detector audit results should be used later to calibrate weights and thresholds.
