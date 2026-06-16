# DeepSeek Live Smoke Log

## Summary

Used the user's explicit authorization to send fixture material to the configured external API and ran a live DeepSeek smoke test.

## Changes

- Added schema-specific prompts for `SemanticRepresentation`, `AcademicProfile`, `CandidateRevisions`, and `RefinedCandidate`.
- Added schema-validation repair when a provider returns valid JSON that does not match the expected Pydantic shape.
- Added wrapper unwrapping support for nested payloads such as `academic_profile` and `candidate_revisions`.
- Added a regression test for nested provider schema payloads.

## Verification

```sh
python -m pytest
python -m academic_engine.cli run tests/fixtures/political_science.txt -o examples/output/political_science.live-smoke.json --cycles 1
```

Results:

- pytest: `11 passed`
- live DeepSeek smoke: passed
- selected candidate: `candidate-6`
- selected strategy: `non_native_refinement`
- stop reason: `initial_candidate_met_quality_and_detector_targets`
- detector risk: `0.2265`
- hard constraint failures: none

## Detector Status

The CLI still uses the local heuristic detector only. Mainstream external detector adapters are not wired yet.
