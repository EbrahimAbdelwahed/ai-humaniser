# Fast-DetectGPT Unavailable Details Log

## Context

The deployed web app reported only generic detector warnings:

```text
Unavailable optional detector signals: official_fast_detectgpt.
Unavailable detectors: official_fast_detectgpt.
```

That confirms the app is running, but hides the underlying Fast-DetectGPT failure reason from the main warning text.

## Changes

- Updated detection warnings to include each unavailable detector's `error` value when present.
- The detector response already exposed `error` per detector; this change surfaces the same information in the top-level warning.

## Verification

```sh
python -m pytest tests/test_web_app.py -q
python -m py_compile src/academic_engine/web/app.py
```

Both passed locally.

