# Vercel Deploy Log

## Summary

Prepared the FastAPI web prototype for Vercel hosting and documented Fast-DetectGPT production configuration.

## Changed Files

- `api/index.py`
- `requirements.txt`
- `vercel.json`
- `src/academic_engine/web/app.py`
- `src/academic_engine/web/static/app.js`
- `tests/test_web_app.py`
- `.env.example`
- `README.md`
- `dev/plans/2026-06-16-1129--web-prototype--vercel-deploy--plan.md`

## Notes

- Vercel hosts the FastAPI app and static UI.
- Fast-DetectGPT remains an external RunPod-backed official detector route.
- `ACADEMIC_ENGINE_WEB_INLINE_JOBS` defaults to true on Vercel via `VERCEL=1`, avoiding in-memory background polling across serverless requests.
- Fast-DetectGPT is considered configured only when either `ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI` is set or both `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` and `RUNPOD_API_KEY` are available.

## Verification

```sh
python -m py_compile api/index.py src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py
VERCEL=1 python -c "from api.index import app; print(app.title)"
```

All checks passed locally.
