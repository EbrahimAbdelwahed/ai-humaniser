# Blind Thesis GPU Test

Ran a blind detector/pipeline experiment using a real open-access academic text and a DeepSeek-generated text on the same topic.

## Source

Primary source selected from worker research:

- Title: `Beyond Risk and Need: Integrating Strengths-Based Psychological Development into Correctional Rehabilitation`
- Author: Jeffrey L. Bohn
- Repository: University of Pennsylvania ScholarlyCommons
- Source URL: `https://repository.upenn.edu/entities/publication/4f131413-4e17-47d8-80b2-271885f21677`
- PDF URL: `https://repository.upenn.edu/server/api/core/bitstreams/2f318136-2b6a-4d9f-9794-ad91e8efe20c/content`
- License noted by worker: Creative Commons Attribution 4.0 International, item-level metadata.
- Selected section: `The Scale and Cost of Correctional Failure` through before `Positive Psychology: A Foundation for Strengths-Based Interventions`.

Earlier Harvard DASH material was downloaded but not used as the final blind source because its item/PDF rights metadata was less clean (`LAA` / all rights reserved).

## Artifacts

- Source PDF: `experiments/blind_thesis_2026_06_04/source/bohn_capstone_beyond_risk_and_need.pdf`
- Source metadata: `experiments/blind_thesis_2026_06_04/source/bohn_source_metadata.json`
- Longish blind manifest/key: `experiments/blind_thesis_2026_06_04/samples/`
- Short blind manifest/key: `experiments/blind_thesis_2026_06_04/samples_short/`
- Raw local baseline: `experiments/blind_thesis_2026_06_04/results/blind_raw_detector_audit.local.json`
- Raw local+GPU longish: `experiments/blind_thesis_2026_06_04/results/blind_raw_detector_audit.local_flash_gpu.json`
- Raw local+GPU short: `experiments/blind_thesis_2026_06_04/results/blind_raw_detector_audit.short.local_flash_gpu.json`
- Full pipeline short summary: `experiments/blind_thesis_2026_06_04/results/short_full_pipeline_summary.local_flash_gpu.json`
- Full pipeline short artifacts:
  - `experiments/blind_thesis_2026_06_04/results/sample_a.short_full_pipeline_calibration.local_flash_gpu.json`
  - `experiments/blind_thesis_2026_06_04/results/sample_b.short_full_pipeline_calibration.local_flash_gpu.json`

## Blind Key

Short samples:

- `sample_a`: human thesis excerpt, 520 words.
- `sample_b`: DeepSeek-generated section, 520 words.

Longish samples:

- `sample_a`: human thesis excerpt, 906 words.
- `sample_b`: DeepSeek-generated section, 743 words.

## GPU Endpoint

- Deployed endpoint: `academic-engine-detectors-small-v1`
- Endpoint id: `cytff0nh4oxx77`
- GPU target in script: `GpuGroup.AMPERE_16`
- Workers: `(0, 1)`
- Idle timeout: `45`
- Used detector profile: stable `roberta_cluster`
- Runtime detector cluster: RADAR, OpenAI RoBERTa detector, ChatGPT RoBERTa detector.
- Endpoint was undeployed immediately after the runs:

```text
deleted academic-engine-detectors-small-v1
```

## Raw Detector Results

Longish raw local+GPU:

- `sample_a`: risk `0.3856`, consensus `lower_risk`, disagreement `0.5000`
- `sample_b`: risk `0.4618`, consensus `moderate_risk`, disagreement `0.6443`

Short raw local+GPU:

- `sample_a`: risk `0.3643`, consensus `moderate_risk`, disagreement `0.3352`
- `sample_b`: risk `0.4443`, consensus `moderate_risk`, disagreement `0.5708`

Short raw per-detector highlights:

- `sample_a` Flash roberta cluster: `0.4752`
- `sample_b` Flash roberta cluster: `0.4554`
- The separation came mostly from local stylometry/repetition/readability signals, not from the RoBERTa cluster.
- `sample_b` local repetition/genericity was high: `0.7150`.
- `sample_b` local readability academic pattern was high: `0.5981`.

## Full Pipeline Results

The first full-pipeline attempt on ~900-word inputs failed before detector scoring because DeepSeek returned invalid JSON for `CandidateRevisions` even after one repair attempt. This indicates the current seven-candidate JSON schema is too fragile for chapter-length inputs.

The short 520-word full pipeline succeeded:

- `sample_a` selected `candidate-2`, strategy `natural_scholarly`, risk `0.3591`, utility `0.4468`, weighted quality `0.5059`.
- `sample_a` selected candidate had hard citation failures:
  - `(Haney, 2002, p. 15)`
  - `(Alper et al, 2018)`
  - `(Sentencing Project, 2024; Broner et al, 2005)`
  - `(Haney, 2001; Schliehe et al, 2022; Dolovich, 2017)`
- `sample_b` selected `candidate-1-r1`, strategy `natural_scholarly`, risk `0.4306`, utility `0.7981`, weighted quality `0.8399`, no hard failures.

## Interpretation

- The detector stack can run cost-controlled GPU scoring successfully with the batch architecture.
- The current RoBERTa cluster is not very discriminative on this pair; it scored both samples around moderate risk.
- The local stylometry/repetition/readability signals produced the strongest distinction between human and DeepSeek text.
- The full refinement pipeline still has a critical preservation bug/ranking issue: a candidate with citation hard failures was selected for `sample_a`.
- DeepSeek JSON generation is brittle for longer chapter-like inputs under the current schema and candidate count.

## Next Actions

1. Fix final selection so hard-constraint failures cannot be selected unless every candidate fails and the report marks the run as blocked/unsafe.
2. Add chunking or fewer-candidate mode for chapter-length inputs to avoid DeepSeek JSON truncation/invalid JSON.
3. Treat roberta_cluster as weak supporting evidence, not a primary discriminator.
4. Use raw detector audit as a separate first-class command because it is more appropriate for blind source-vs-generated comparisons than the rewrite pipeline.
