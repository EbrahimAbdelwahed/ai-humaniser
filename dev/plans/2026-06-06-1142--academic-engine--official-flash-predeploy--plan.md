# Official Flash Predeploy Plan

## Goal

Prepare the official detector RunPod Flash endpoint for a low-cost deploy/calibration pass without creating billable resources in this step.

## Steps

1. Verify endpoint packaging locally with `flash build` if possible.
2. Verify the endpoint source can be imported and exposes `health`/`model_inventory` without a deployed endpoint.
3. Add a reusable calibration runner or runbook for the three thesis samples after `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` is configured.
4. Record failure modes and next deploy command.

## Constraints

- Do not run `flash deploy` without explicit approval.
- Do not create billable RunPod resources in this phase.
- Do not print `.env` secrets.
- Keep GPU defaults at `ADA_24`/`AMPERE_24`, not 80GB.
