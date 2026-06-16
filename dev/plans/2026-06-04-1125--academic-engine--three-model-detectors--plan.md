# Three Model Detector Signals Plan

## Goal

Make the stable Flash detector profile useful by using at least three model-backed detector signals while keeping GPU cost bounded.

## Selected Stable Signals

- `radar`: `Shushant/adal-roberta-detector`
- `openai_roberta`: `openai-community/roberta-base-openai-detector`
- `chatgpt_roberta`: `Hello-SimpleAI/chatgpt-detector-roberta`

## Rationale

All three are Hugging Face sequence-classification models, so they should fit on smaller GPU SKUs much better than causal-LM/perplexity methods.

## Work

1. Add new Flash detector names to config profiles and endpoint ids.
2. Add endpoint branches for the two RoBERTa detector models.
3. Improve AI-label index inference for generic sequence classifiers.
4. Adjust consensus weights and tests.
5. Verify locally without deploying GPU resources.
