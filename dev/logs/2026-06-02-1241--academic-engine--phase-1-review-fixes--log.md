# Log: Phase 1 Review Fixes

## Work

- Reviewed the worker implementation for Phase 1.
- Re-ran the test suite.
- Exercised CLI `run` and `experiment` in mock-provider mode.
- Patched citation extraction to preserve narrative citations such as `Smith (2021)`.
- Patched refinement stop logic to evaluate the current refinement score instead of the initial ranked score.
- Patched final selection to choose the best hard-constraint-safe candidate instead of blindly selecting the last refinement cycle.
- Added one-retry JSON repair handling around LLM stage calls.
- Added `.env` file loading to `EngineConfig.from_env()` so a local DeepSeek key file works without manually exporting variables.
- Added regression tests for citation extraction, unsafe refinement rejection, and `.env` loading.

## Verification

```text
python -m pytest
academic-engine run examples/input/political_science.txt -o examples/output/political_science.result.json --mock-provider --cycles 1
academic-engine experiment tests/fixtures -o examples/output/experiment-summary.json --mock-provider --cycles 1
```

Result:

```text
10 passed
```

## Notes

- Live DeepSeek calls were not exercised in this review pass.
- External detector integrations remain adapter placeholders.
- Mock-provider output is only a deterministic harness; real writing quality depends on DeepSeek prompt behavior.
