# Community Detectors Review Log

## Summary

Reviewed the community detector worker patch, fixed practical runtime issues, and verified Binoculars through a Python 3.11 side environment.

## Changes

- Added `scripts/community/binoculars_cli.py`, a stdin-to-JSON wrapper for the official Binoculars package.
- Added `community_candidate_limit` config/CLI/env support so expensive community detectors run only on the top-K locally ranked candidates for `local+community`/`all`.
- Ensured the final selected candidate is always audited by configured community detectors before the final report.
- Increased community CLI timeout from 120s to 300s because model startup on M1 can exceed two minutes.
- Fixed `DeterministicMockProvider` text extraction so prompt text such as `Return JSON only.` does not leak into mock rewrites.
- Added a regression assertion that final output does not contain `Return JSON only`.

## Verification

```sh
python -m pytest
/opt/homebrew/bin/python3.11 -m venv /private/tmp/academic-engine-binoculars-py311
/private/tmp/academic-engine-binoculars-py311/bin/python -m pip install git+https://github.com/ahans30/Binoculars.git
```

Results:

- pytest: `23 passed`
- Binoculars installed successfully in the Python 3.11 venv
- Binoculars provider smoke with `sshleifer/tiny-gpt2`: available, score `0.4451`, label `moderate_risk`
- Pipeline smoke with `local+community`, `community_candidate_limit=1`, and Binoculars tiny: passed

## Detector Status

- `community_binoculars`: adapter works, official package installed in `/private/tmp/academic-engine-binoculars-py311`; smoke used tiny models for feasibility, not calibrated production models.
- `community_ghostbuster`: adapter/wrapper is implemented; no local CLI is configured yet.
- `community_mage`: adapter/wrapper is implemented; no local CLI is configured yet.
- `community_radar`: adapter/wrapper is implemented; no local CLI is configured yet.

## Notes

- Binoculars official default models are Falcon 7B variants and are likely too heavy for comfortable repeated use on a 16GB MacBook Pro unless carefully cached/quantized or run as a persistent side service.
- CLI wrappers are practical for smoke tests, but repeated subprocess model loading is slow. A persistent local detector service is the next engineering step for real iterative refinement.
- The current Binoculars tiny run is a wiring test, not a meaningful detector calibration.
