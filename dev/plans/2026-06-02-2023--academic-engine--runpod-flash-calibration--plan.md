# RunPod Flash Calibration Plan

## Scope

Add a modular RunPod Flash detector provider and a calibration/audit mode that sends every generated/refined candidate to teacher detectors when requested.

## Steps

1. Inspect detector provider selection, pipeline candidate lifecycle, scoring, CLI output, and existing community top-K behavior.
2. Add Flash detector config/env parsing and detector-set aliases without exposing secret values.
3. Implement an offline-safe Flash provider that returns standard detector results and unavailable errors when `runpod_flash` or endpoint configuration is missing.
4. Add calibration/research behavior so configured teacher detectors audit all candidates instead of only top-K.
5. Add `academic-engine calibrate` artifact output with candidate metadata, detector scores, quality/preservation, and notes.
6. Add minimal `scripts/runpod_flash/` endpoint code following Flash gotchas, with Binoculars implemented and other detectors as explicit skeleton fallbacks.
7. Add offline tests and run pytest plus CLI mock smoke.
8. Write a dev log and update `dev/index.md` with the important new reference.
