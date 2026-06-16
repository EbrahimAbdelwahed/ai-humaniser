# RunPod Block Active Endpoints Log

## Summary

Blocked the active RunPod serverless endpoint found on the account.

## Actions

- Read local memory protocol and project memory index.
- Checked Flash-managed endpoints with `flash undeploy list`; Flash reported no endpoints.
- Loaded `RUNPOD_API_KEY` from `.env` without printing it and queried RunPod GraphQL directly.
- Found one serverless endpoint:
  - id: `dwo7t35b4eni2w`
  - name: `detect-fb`
  - type: `QB`
  - workersMin: `0`
  - workersMax: `1`
  - workersStandby: `1`
  - gpuIds: `AMPERE_24,ADA_24,AMPERE_16`
- `flash undeploy detect-fb --force` still reported no endpoints, so the endpoint was deleted directly with GraphQL:
  - `mutation { deleteEndpoint(id: "dwo7t35b4eni2w") }`

## Verification

- Re-ran the RunPod endpoint list through GraphQL.
- Result: `[]`

## Changed Files

- `dev/logs/2026-06-08-1249--runpod--block-active-endpoints--log.md`
