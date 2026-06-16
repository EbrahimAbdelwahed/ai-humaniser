# Web Prototype Curated Detector Humanizer Site Log

## Summary

Refined the existing FastAPI/static web prototype into a more polished detector/refinement tool and tightened the Fast-DetectGPT web contract.

## Changed Files

- `src/academic_engine/web/app.py`
- `src/academic_engine/web/static/index.html`
- `src/academic_engine/web/static/styles.css`
- `src/academic_engine/web/static/app.js`
- `tests/test_web_app.py`
- `README.md`
- `dev/plans/2026-06-11-1718--web-prototype--curated-detector-humanizer-site--plan.md`
- `dev/logs/2026-06-11-1718--web-prototype--curated-detector-humanizer-site--log.md`

## Backend Notes

- `/health` now reports:
  - available detector presets
  - whether official Fast-DetectGPT is configured
  - route type (`runpod_flash` or CLI)
  - timeout seconds
  - DeepSeek/refinement provider configuration status
- Detection/refinement responses now include `requested_detector_preset`.
- The web-only `local+fast-detectgpt` preset expands to local detectors plus `official_fast_detectgpt` only.
- `local+fast-detectgpt` no longer pulls in `official_binoculars` or `official_ghostbuster`, avoiding noisy unavailable warnings in the web app.

## Frontend Notes

- Replaced the MVP layout with a denser product-tool interface:
  - backend/Fast readiness pills
  - two workflow cards: Detector and AI Humanizer
  - word count and current limit
  - compact summary metrics
  - detector stack rows with availability badges
  - copyable output
  - explicit notes about local vs remote detector calls
- Fixed a CSS issue where `[hidden]` form fields were displayed by label styles, causing detector mode controls to overflow.

## RunPod State

Checked RunPod Flash endpoint list without deploying:

- `detect-fb`
- endpoint id: `dwo7t35b4eni2w`
- state: inactive

The local web server was started with `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=dwo7t35b4eni2w`, so the UI reports Fast-DetectGPT as ready. No detector GPU scoring run was triggered during this verification.

## Verification

Commands:

```sh
python -m py_compile src/academic_engine/web/app.py
python -m pytest tests/test_web_app.py -q
python -m pytest -q
```

Results:

- `tests/test_web_app.py`: 8 passed
- full suite: 77 passed

Browser verification:

- Opened `http://127.0.0.1:8000/` in the in-app browser.
- Confirmed health display: backend ready and Fast-DetectGPT ready via `runpod_flash`.
- Ran a local detector job from the UI.
- Result: `detect · succeeded`, six local detector rows rendered, copy output enabled.
