# Vercel Runtime Dependencies Fix Log

## Summary

Fixed Vercel import failure where `create_app()` raised:

```text
RuntimeError: Web dependencies are not installed. Install with `pip install -e .[web]`.
```

## Cause

Vercel build logs show dependency installation from `pyproject.toml`. `fastapi` and `uvicorn` were only listed under the optional `web` extra, so the deployed function did not install them.

## Changes

- Moved `fastapi>=0.111` and `uvicorn>=0.30` into main `project.dependencies`.
- Left the optional `web` extra as an empty compatibility extra.
- Updated the missing-dependency message in `src/academic_engine/web/app.py`.

## Verification

```sh
VERCEL=1 python -c "from api.index import app, fastapi_app; import inspect; print(inspect.iscoroutinefunction(app), callable(app), fastapi_app.title)"
python -m py_compile api/index.py src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py
```

All checks passed locally.
