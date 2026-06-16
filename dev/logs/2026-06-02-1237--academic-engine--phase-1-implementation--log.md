# Log: Academic Engine Phase 1 Implementation

## Summary

Implemented the Phase 1 Python CLI-first academic writing refinement engine.

## Implemented Files

- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/academic_engine/**`
- `src/academic_engine/prompts/**`
- `tests/**`
- `tests/fixtures/**`
- `examples/input/**`
- `examples/output/**`
- `runs/.gitkeep`

## Runtime Behavior

- Product runtime provider is OpenAI-compatible and configured through:
  - `DEEPSEEK_API_KEY`
  - `DEEPSEEK_BASE_URL`
  - `DEEPSEEK_MODEL`
- Default model is `deepseek-v4-flash`.
- If no DeepSeek key is available, or `--mock-provider` is passed, the engine uses a deterministic mock provider for tests and examples.
- CLI supports:
  - `academic-engine run <input> -o <output>`
  - `academic-engine experiment <fixture-dir> -o <output>`
- Run artifacts are written under `runs/`.
- Detector signals are included in candidate scoring, ranking, refinement, final report, and experiment summaries.
- A local heuristic detector provider is included so tests do not depend on external detector accounts.

## Verification

Commands run:

```sh
python -m pytest
academic-engine run examples/input/political_science.txt -o examples/output/political_science.result.json --mock-provider --cycles 1
academic-engine experiment tests/fixtures -o examples/output/experiment-summary.json --mock-provider --cycles 1
python -m json.tool examples/output/political_science.result.json >/dev/null
python -m json.tool examples/output/experiment-summary.json >/dev/null
```

Result:

- `python -m pytest`: 7 passed.
- CLI single-run and experiment outputs were valid JSON.

## Notes

- The first test run failed because `pydantic` was not installed.
- The first editable install attempt exposed a Hatch package-selection issue; `tool.hatch.build.targets.wheel.packages = ["src/academic_engine"]` fixed it.
- DeepSeek live calls were not exercised because the verification used deterministic mock mode.
