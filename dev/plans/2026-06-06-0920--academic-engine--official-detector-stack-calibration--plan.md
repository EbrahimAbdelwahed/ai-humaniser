# Official Detector Stack Calibration Plan

## Goal

Implement and stabilize official or near-official detector integrations for:

- `ghostbuster_official`
- `binoculars_official`
- `fast_detectgpt`

Then calibrate the pipeline against the provided thesis-derived documents:

- `_capitolo2_docx.txt`: AI-generated
- `_introduzione_capitolo1.txt`: human-generated first paragraph
- `Il potere persuasivo della musica.docx`: AI-generated

The target is a richer detector signal that ranks the AI-generated thesis samples higher risk than the human sample while preserving clear failure modes, cost controls, and offline-safe fallbacks.

## Safety and Product Framing

- Treat detector results as diagnostic signals, not truth labels.
- Do not promise guaranteed detection or undetectability.
- The calibration target is false-positive-aware artificiality/naturalness risk scoring.
- Preserve the raw text samples as evaluation fixtures; do not overwrite user-provided files.

## Architecture

Add an official detector layer alongside existing local/community/flash providers:

```text
detector_set = local+official

official_binoculars:
  family: zero_shot_cross_perplexity
  preferred runtime: local official package if installed, otherwise configured CLI/API fallback
  failure mode: detector_unavailable, model_load_failed, timeout

official_ghostbuster:
  family: feature_based_learned_detector
  preferred runtime: configured local CLI/wrapper around official repo
  failure mode: detector_unavailable, model_assets_missing, timeout

official_fast_detectgpt:
  family: zero_shot_probability_curvature
  preferred runtime: configured local CLI/wrapper around official repo or pydetectgpt-compatible wrapper
  failure mode: detector_unavailable, model_load_failed, timeout
```

Expose normalized results using the existing `DetectorResult` schema:

- provider name
- provider kind
- score in `[0, 1]`
- label
- confidence
- raw detector output
- error and failure mode if unavailable
- input hash

## Profiles

```text
raw_stable:
  - local ensemble
  - official_ghostbuster
  - official_binoculars

calibration_v3:
  - raw_stable
  - official_fast_detectgpt
  - roberta_cluster low weight if GPU endpoint configured

research:
  - calibration_v3
  - full DetectGPT-like methods later
  - benchmark harness later
```

## Implementation Steps

1. Inspect current detector adapters, config, CLI, and scoring weights.
2. Add config/env fields for official detector CLIs and runtime limits.
3. Add official detector provider classes:
   - official Binoculars provider/wrapper
   - official Ghostbuster CLI provider
   - Fast-DetectGPT CLI/provider
4. Add `local+official`, `official`, and `all` detector-set routing.
5. Add tests for:
   - unavailable fallback
   - parse JSON/numeric CLI outputs
   - scoring weight inclusion
   - raw-audit artifact shape
6. Prepare calibration fixtures from the three provided thesis files.
7. Run `raw-audit` on the fixture set with local + official detectors.
8. Iterate weights/thresholds only after observing detector behavior.

## Subagent Split

Worker A: detector implementation

- Owns `src/academic_engine/config.py`, `src/academic_engine/detectors.py`, `src/academic_engine/scoring.py`, detector tests.
- Adds provider classes and routing.
- Must not deploy RunPod or read/print secrets.

Worker B: thesis fixture extraction and calibration harness

- Owns `experiments/thesis_calibration_2026_06_06/`, fixture generation scripts/artifacts, raw-audit summaries.
- Extracts DOCX text using local document tooling.
- Must not modify detector code.

Coordinator

- Reviews/patches integration.
- Runs tests.
- Decides whether external installs/API/GPU are needed, requesting approval before network/billable operations.

## Initial Acceptance Criteria

- `python -m pytest` passes.
- `raw-audit` can run on the three provided thesis samples without crashing.
- Official detector providers return either valid normalized scores or explicit unavailable results.
- Calibration artifact records which official detectors were available/unavailable and why.
- No RunPod resource is deployed without explicit approval.

## Sources

- Binoculars: `https://github.com/ahans30/Binoculars`
- Binoculars paper: `https://proceedings.mlr.press/v235/hans24a.html`
- Ghostbuster paper: `https://arxiv.org/abs/2305.15047`
- Ghostbuster code reference: `https://github.com/vivek3141/ghostbuster`
- Fast-DetectGPT: `https://github.com/baoguangsheng/fast-detect-gpt`
- Fast-DetectGPT paper: `https://arxiv.org/abs/2310.05130`
