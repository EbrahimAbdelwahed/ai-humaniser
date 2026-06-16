# Sample Detector Comparison Log

## Summary

Created a synthetic AI-ish political science sample and ran it through the live DeepSeek pipeline with the local detector ensemble.

## Files

- Input sample: `examples/input/comparison_aiish_political_science.txt`
- Pipeline output: `examples/output/comparison_aiish_political_science.result.json`

## Detector Set

Used `--detectors local`, which runs:

- `local_stylometry_burstiness`
- `local_lexical_diversity`
- `local_gltr_lite_probability_shape`
- `local_repetition_genericity`
- `local_readability_academic_pattern`
- `local_heuristic_detector_risk`

## Results

Before:

- aggregate detector risk: `0.3514`
- label consensus: `lower_risk`
- disagreement: `0.4372`
- per-detector scores:
  - `local_stylometry_burstiness`: `0.5972`
  - `local_lexical_diversity`: `0.1600`
  - `local_gltr_lite_probability_shape`: `0.1720`
  - `local_repetition_genericity`: `0.4950`
  - `local_readability_academic_pattern`: `0.2361`
  - `local_heuristic_detector_risk`: `0.3321`

After:

- aggregate detector risk: `0.2519`
- label consensus: `lower_risk`
- disagreement: `0.4395`
- per-detector scores:
  - `local_stylometry_burstiness`: `0.5595`
  - `local_lexical_diversity`: `0.1600`
  - `local_gltr_lite_probability_shape`: `0.1400`
  - `local_repetition_genericity`: `0.1200`
  - `local_readability_academic_pattern`: `0.2503`
  - `local_heuristic_detector_risk`: `0.2460`

Semantic preservation:

- citations preserved: yes
- numeric values preserved: yes
- hard constraint failures: none

## Notes

- The largest improvement came from repetition/genericity markers.
- Stylometry/burstiness remained moderately high, so the next refinement prompt should target sentence-length variation without changing claims.
- Local scores are diagnostic and should be calibrated against later online detector audits.
