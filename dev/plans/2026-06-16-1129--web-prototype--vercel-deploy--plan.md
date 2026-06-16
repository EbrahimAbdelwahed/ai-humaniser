# Vercel Deploy Plan

## Goal

Make the FastAPI web prototype deployable on Vercel and document the environment needed for Fast-DetectGPT through the existing RunPod-backed official detector route.

## Constraints

- Do not commit or print secret values.
- Keep Fast-DetectGPT execution outside Vercel because it requires GPU/serverless detector infrastructure.
- Avoid depending on in-memory background polling on Vercel serverless.

## Steps

1. Add Vercel Python entrypoint and dependency file.
2. Add Vercel routing configuration.
3. Make web job submission compatible with serverless inline execution.
4. Document Vercel deploy commands and required environment variables.
5. Verify with tests and lightweight import/compile checks.
