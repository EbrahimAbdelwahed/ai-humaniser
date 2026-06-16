# Three Model Detector Signals Log

## Summary

Updated the stable Flash detector profile from one model-backed signal to three model-backed sequence-classification signals.

## Stable Flash Detectors

- `flash_radar`
  - model: `Shushant/adal-roberta-detector`
  - type: Hugging Face sequence classification
- `flash_openai_roberta`
  - model: `openai-community/roberta-base-openai-detector`
  - type: Hugging Face sequence classification
- `flash_chatgpt_roberta`
  - model: `Hello-SimpleAI/chatgpt-detector-roberta`
  - type: Hugging Face sequence classification

## Cost Guardrails

- The Flash endpoint remains configured for `GpuGroup.AMPERE_16`.
- `idle_timeout` remains `45`.
- Binoculars remains out of the stable profile because it loads two causal language models and is currently an approximate signal.
- Ghostbuster remains out of the stable profile because it is currently a feature proxy.
- No RunPod deploy was performed during this change.

## Changes

- `src/academic_engine/config.py`
  - `stable` profile is now `radar`, `openai_roberta`, `chatgpt_roberta`.
  - `experimental` and `all` profiles include the stable detectors plus non-stable signals.
  - Added detector-specific endpoint env support for OpenAI RoBERTa and ChatGPT RoBERTa.
- `src/academic_engine/detectors.py`
  - Added `openai_roberta` and `chatgpt_roberta` to supported/stable Flash detector names.
- `src/academic_engine/scoring.py`
  - Added consensus weights for the two new Flash detectors.
- `scripts/runpod_flash/detectors_endpoint.py`
  - Added endpoint branches for `openai_roberta` and `chatgpt_roberta`.
  - Added AI-label index inference from `id2label` metadata for generic sequence classifiers.

## Verification

```text
python -m py_compile scripts/runpod_flash/detectors_endpoint.py src/academic_engine/config.py src/academic_engine/detectors.py src/academic_engine/scoring.py
python -m pytest
```

Result: `32 passed`.
