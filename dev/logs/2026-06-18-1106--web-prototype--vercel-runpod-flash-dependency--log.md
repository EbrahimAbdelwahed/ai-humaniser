# Vercel RunPod Flash Dependency Log

## Context

Vercel runtime logs reported:

```text
runpod_flash is not installed or importable: No module named 'runpod_flash'
```

The project previously declared `runpod-flash` only in the optional `flash` extra, but Vercel installs required dependencies from `pyproject.toml` and does not install extras for the deployed function.

## Changes

- Added `runpod-flash>=1.7.0` to main `project.dependencies`.
- Kept the `flash` optional extra present but empty for compatibility with existing install commands.
- Added `runpod-flash>=1.7.0` to `requirements.txt` for parity with local or alternate installers.

## Verification

```sh
python -m pytest tests/test_web_app.py -q
python -m py_compile api/index.py src/academic_engine/web/app.py src/academic_engine/detectors.py
```

Both passed locally.

