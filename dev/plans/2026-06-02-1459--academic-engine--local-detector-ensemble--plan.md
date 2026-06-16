# Local Detector Ensemble Plan

## Scope

Implement a lightweight local detector ensemble for CLI diagnostics, plus optional HuggingFace detector support when dependencies and model files already exist locally.

## Constraints

- Do not call external APIs.
- Do not install packages or trigger model downloads.
- Do not read or print `.env` contents.
- Keep edits to authorized files.
- Preserve semantic hard constraints as the final-selection gate.

## Steps

1. Refactor local detector providers into multiple always-available heuristic signals:
   - stylometry/burstiness
   - lexical diversity
   - GLTR-lite/probability-shape
   - repetition/genericity
   - readability/academic-pattern risk
2. Add optional HuggingFace adapter for `openai-community/roberta-base-openai-detector` or configured local model path/name, returning `available=false` on missing dependencies or local files.
3. Add env/CLI detector selection:
   - default lightweight local ensemble
   - `hf` optional inclusion
4. Update consensus scoring with documented weights and disagreement from available detectors.
5. Ensure CLI report JSON exposes per-candidate/final detector details and readable consensus.
6. Add tests for default ensemble, optional unavailability, consensus/disagreement, and hard constraints.
7. Run pytest and mock CLI smoke checks, including a forced-cycle run with strict thresholds if practical.
8. Write implementation log and update `dev/index.md`.
