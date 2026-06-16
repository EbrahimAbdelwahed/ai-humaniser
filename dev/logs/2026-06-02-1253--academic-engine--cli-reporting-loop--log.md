# CLI Reporting Loop Log

## Summary

Improved the CLI refinement report payload so each run exposes a stable, testable summary of the loop outcome.

## Changes

- Added final-report metadata for:
  - selected candidate id, strategy, source, rank/cycle, utility, quality, detector risk, and hard constraint failures
  - stop reason for the refinement loop
  - cycle-by-cycle loop rows with score, detector risk, detector consensus, constraint failures, and notes
  - non-disruptive-change summary with preservation gate, score, semantic/factual scores, and word-count delta
- Updated experiment summaries to use the selected final candidate score rather than assuming the last refinement cycle or top-ranked candidate was final.
- Added regression assertions for reporting fields and unsafe-refinement fallback behavior.

## Verification

```sh
python -m academic_engine.cli run examples/input/political_science.txt -o examples/output/political_science.result.json --mock-provider --cycles 1
python -m academic_engine.cli experiment tests/fixtures -o examples/output/experiment-summary.json --mock-provider --cycles 1
pytest
```

Result: `10 passed`.

## Live DeepSeek Smoke

`DEEPSEEK_API_KEY` was detected as configured without printing the key or `.env` contents.

The live smoke command was attempted:

```sh
python -m academic_engine.cli run tests/fixtures/political_science.txt -o examples/output/political_science.live-smoke.json --cycles 1
```

It failed with a DNS/connectivity error before receiving a DeepSeek response.

An escalated retry request for the same command was rejected because it would send workspace fixture text to an external API. No workaround was attempted.

## Changed Files

- `src/academic_engine/pipeline.py`
- `tests/test_pipeline_contract.py`
- `examples/output/political_science.result.json`
- `examples/output/experiment-summary.json`
- `dev/logs/2026-06-02-1253--academic-engine--cli-reporting-loop--log.md`
- `dev/index.md`
