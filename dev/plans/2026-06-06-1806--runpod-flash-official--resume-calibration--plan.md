# RunPod Flash Official Resume Calibration Plan

## Goal

Resume official detector GPU calibration after network recovery and iterate until at least one useful official detector signal runs on thesis fixtures.

## Steps

1. Fix local official provider timeout so RunPod Flash subprocesses are not killed at 300s when the Flash timeout is higher.
2. Add an endpoint `bootstrap` operation that installs/clones runtime assets without requiring text scoring.
3. Add client support for direct non-scoring endpoint operations.
4. Verify tests locally.
5. Deploy the updated official Flash app on cost-controlled 24GB GPU, workers `(0, 1)`, using a smaller same-tokenizer Binoculars model pair for iterative calibration.
6. Run `health`, `model_inventory`, then `bootstrap` before any thesis scoring.
7. Run calibration on thesis fixtures only after at least one official detector reports available or a clear model/runtime failure mode.

## Cost Guardrails

- Keep GPU classes at `ADA_24`/`AMPERE_24` for iterative calibration.
- Use 48GB only for official Falcon-7B Binoculars calibration if explicitly needed; 24GB OOMs on that pair.
- Keep workers `(0, 1)`.
- Do not use 80GB GPUs unless explicitly re-approved.
- Prefer one detector at a time during bootstrap/scoring.
