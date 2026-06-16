# Web Prototype Detector Refinement MVP Log

## Summary

Implemented the web prototype surface for detector-only analysis and diagnostic refinement on top of the existing academic engine.

## Changed Files

- `src/academic_engine/web/__init__.py`
- `src/academic_engine/web/app.py`
- `src/academic_engine/web/static/index.html`
- `src/academic_engine/web/static/styles.css`
- `src/academic_engine/web/static/app.js`
- `tests/test_web_app.py`
- `pyproject.toml`
- `README.md`

## Notes

- FastAPI remains optional; importing the module without the web extra does not require starting the app.
- The in-memory job runner exposes queued, running, succeeded, and failed job states.
- Web settings are controlled with `ACADEMIC_ENGINE_WEB_MAX_WORDS` and `ACADEMIC_ENGINE_WEB_WORKERS`.
- Detector presets are `local`, `local+official`, and `official-fast-detectgpt`.
- DTO summaries omit detector raw payloads and input hashes.
- Web refinement calls `run_text(..., write_artifact=False)`.
- No deploy, network call, or RunPod call was performed.

## Verification

```sh
python -m py_compile src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py -q
```

Result: 5 focused web tests passed.

## Coordinator Review

After worker completion, coordinator review made these adjustments:

- `run_detection(...)` now uses the shared detector summary DTO, including available/unavailable detector counts.
- `run_refinement(...)` now includes `summary.risk`, `summary.consensus`, and `summary.disagreement` so the frontend can render both modes consistently.
- The Refine form now sends `detector_execution` explicitly.
- `/` serves `src/academic_engine/web/static/index.html` when present, leaving the inline page only as a fallback.

Additional verification:

```sh
python -m py_compile src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py -q
python -m pytest -q
```

Result: 74 tests passed.

Local HTTP smoke:

- `GET /health`: returned `status=ok`, `max_words=4000`, `workers=1`.
- `POST /api/detect` with local detectors: succeeded with risk `0.2776` and 6 detector signals.
- `POST /api/refine` with `mock_provider=true` and local detectors: succeeded with before risk `0.2776`, after risk `0.2855`, and a refined text.
