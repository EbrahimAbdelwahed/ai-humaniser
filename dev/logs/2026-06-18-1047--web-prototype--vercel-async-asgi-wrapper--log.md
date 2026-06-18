# Vercel Async ASGI Wrapper Log

## Summary

Updated the Vercel entrypoint after Vercel continued to report:

```text
Could not determine the application interface for 'api.index:app'
```

## Changes

- `api/index.py` now exports an async ASGI callable named `app`.
- The FastAPI instance is kept as `fastapi_app` and the exported `app(scope, receive, send)` delegates to it.
- `tests/test_web_app.py` now checks `inspect.iscoroutinefunction(api.index.app)`.

## Verification

```sh
VERCEL=1 python -c "from api.index import app, fastapi_app; import inspect; print(inspect.iscoroutinefunction(app), callable(app), fastapi_app.title)"
python -m py_compile api/index.py src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py
```

All checks passed locally.
