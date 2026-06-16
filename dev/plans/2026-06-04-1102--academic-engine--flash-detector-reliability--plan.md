# Flash Detector Reliability Plan

## Goal

Make GPU detector access reliable enough for the refinement pipeline to use deliberately, with explicit separation between stable model-backed signals and experimental/proxy signals.

## Scope

1. Clarify Flash detector defaults so known-broken detectors are not included by default.
2. Add a detector profile concept for stable, experimental, and all Flash detector sets.
3. Add a CLI health check that pings configured Flash detectors before expensive refinement/calibration runs.
4. Mark endpoint outputs with implementation kind so reports show whether a signal is model-backed or approximate/proxy.
5. Update tests and memory logs.

## Non-Goals

- Do not claim detector evasion or guaranteed undetectability.
- Do not silently hide experimental detector failures.
- Do not rewrite the webapp layer in this pass.
