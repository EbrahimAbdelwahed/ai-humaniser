# Blind Thesis Detector Test Plan

## Goal

Run a short blind comparison between:

1. a real open-access thesis/dissertation chapter excerpt;
2. a DeepSeek-generated chapter-like text on the same topic and comparable length.

Both texts should be sent through the same detector/calibration path, including GPU Flash detectors if configured and cost-safe.

## Constraints

- Keep excerpts short enough to control cost and latency, target about 700-1200 words per text.
- Prefer a source with visible Creative Commons/open-access rights.
- Do not expose secrets from `.env`.
- Do not paste long copyrighted text into responses.
- Use cost-first GPU behavior: small Flash endpoint/profile only, no broad experimental detector fan-out unless explicitly needed.
- Preserve blind labels during scoring so we do not bias interpretation.

## Steps

1. Source selection
   - Use web search to find an open-access thesis/dissertation in a high-volume academic domain.
   - Confirm title, author, repository, PDF URL, license/rights statement, and topic.

2. Text extraction
   - Download the PDF into a local experiment folder.
   - Extract text locally.
   - Select a short coherent chapter/section excerpt.
   - Save metadata separately from blind sample labels.

3. DeepSeek generation
   - Generate a chapter-like text with the same topic, register, and approximate length.
   - Do not use the thesis excerpt as text to copy; use only topic/outline metadata.
   - Save as the second blind sample.

4. Blind packaging
   - Randomize/assign labels such as `sample_a` and `sample_b`.
   - Keep a private key file mapping labels to source type.

5. Detector run
   - Run both samples through calibration/detector path.
   - Use local detectors plus Flash GPU detectors when configured.
   - Keep batch small and sequential if needed.

6. Analysis
   - Compare detector risk, per-detector scores, disagreement, unavailable detectors, and failure modes.
   - Decide whether next work should focus on detector reliability, prompt generation, ranking weights, or source-length normalization.

7. Logging
   - Save commands, artifact paths, source metadata, and observed scores in `dev/logs/`.
