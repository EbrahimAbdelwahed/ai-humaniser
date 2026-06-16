# RunPod Cost Control Log

## Summary

Reduced RunPod Flash cost exposure after discovering the detector endpoint was overprovisioned on `AMPERE_80`.

## Actions

- Listed active Flash endpoints.
- Found 7 active detector endpoints:
  - `academic-engine-detectors`
  - `academic-engine-detectors-v2`
  - `academic-engine-detectors-v3`
  - `academic-engine-detectors-v4`
  - `academic-engine-detectors-v5`
  - `academic-engine-detectors-v6`
  - `academic-engine-detectors-v7`
- Undeployed all 7 endpoints with `flash undeploy --all --force`.
- Verified RunPod Flash now reports `no endpoints found`.
- Changed `scripts/runpod_flash/detectors_endpoint.py`:
  - endpoint name: `academic-engine-detectors-small-v1`
  - GPU: `GpuGroup.AMPERE_16`
  - idle timeout: `45`
- Changed default Flash detector profile to call only `radar`.
- Kept Binoculars out of the stable/default profile because it is an approximate signal that loads two causal LMs.

## Current Cost Posture

There are no active RunPod Flash endpoints from this project at the time of this log.

The next deploy should be explicitly approved and should use the small endpoint:

```text
academic-engine-detectors-small-v1
GpuGroup.AMPERE_16
stable detector profile: radar only
```

## Verification

```text
python -m pytest
```

Result: `32 passed`.
