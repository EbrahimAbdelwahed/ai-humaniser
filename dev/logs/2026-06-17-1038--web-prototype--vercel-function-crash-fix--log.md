# Vercel Function Crash Fix Log

## Summary

Hardened the Vercel Python function entrypoint after a production `FUNCTION_INVOCATION_FAILED` screenshot.

## Changes

- `api/index.py` now prepends the repository `src/` directory to `sys.path` before importing `academic_engine`.
- `requirements.txt` now lists runtime dependencies explicitly instead of relying on editable install syntax.

## Rationale

The previous `requirements.txt` used `-e .[web]`, which requires Vercel to perform an editable install of the local package and its build backend before `api/index.py` can import `academic_engine`. Explicit dependencies plus `src/` path setup make the serverless import path deterministic.

## Verification

```sh
VERCEL=1 python -c "from api.index import app; print(type(app).__name__, app.title)"
python -m py_compile api/index.py src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py
```

All checks passed locally.
