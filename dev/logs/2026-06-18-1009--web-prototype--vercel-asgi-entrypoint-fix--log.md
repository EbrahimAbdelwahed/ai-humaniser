# Vercel ASGI Entrypoint Fix Log

## Summary

Fixed Vercel runtime error:

```text
Could not determine the application interface for 'api.index:app'
```

## Changes

- `api/index.py` now imports `create_app()` and assigns `app = create_app()` directly.
- `src/academic_engine/web/app.py` no longer swallows `create_app()` exceptions and silently sets `app = None`.
- `tests/test_web_app.py` now verifies that `api.index:app` is callable and exposes the expected FastAPI app.

## Verification

```sh
VERCEL=1 python -c "from api.index import app; import inspect; print(type(app).__name__, app.title, callable(app), inspect.iscoroutinefunction(app.__call__))"
python -m py_compile api/index.py src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py
```

All checks passed locally.
