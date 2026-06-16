# Web Prototype Detector Refinement MVP Plan

## Goal

Expose the existing academic engine as a first online prototype for feedback collection.

The MVP must support:

- Detector-only analysis for pasted text.
- Diagnostic refinement for pasted text.
- Local detector execution plus optional official Fast-DetectGPT through the existing RunPod-backed detector configuration.
- A web UI simple enough to deploy quickly and validate user feedback.

## Constraints

- Do not rewrite the existing engine.
- Keep detector/refinement logic in `academic_engine.pipeline`.
- Treat Fast-DetectGPT as optional/configured; if RunPod or endpoint env is missing, surface unavailable detector status instead of failing the web request.
- Keep text private by default: no public URLs containing text, no unnecessary logging of request body content.
- Add length and concurrency controls so the prototype cannot accidentally create runaway cost.
- The UI must make clear that detector scores are diagnostic signals, not guarantees.

## Implementation Shape

1. Add a small web package under `src/academic_engine/web/`.
2. Use FastAPI if available, with a local fallback failure message if web extras are not installed.
3. Add a lightweight in-memory job runner:
   - `POST /api/detect`
   - `POST /api/refine`
   - `GET /api/jobs/{job_id}`
   - `GET /health`
4. Add a browser UI served by the same app:
   - two tabs: `Detector` and `Refine`
   - textarea input
   - detector preset selector
   - status polling
   - compact before/after report
5. Add a web console entrypoint:
   - `academic-engine-web = academic_engine.web.app:main`
6. Add focused tests for:
   - job submission and polling using mock provider/local detectors
   - input length validation
   - result summarization shape

## API Contract

`POST /api/detect`

```json
{
  "text": "string",
  "detectors": "local|local+official|official-fast-detectgpt",
  "detector_execution": "sequential|parallel"
}
```

Returns:

```json
{
  "job_id": "string",
  "status": "queued"
}
```

`POST /api/refine`

```json
{
  "text": "string",
  "detectors": "local|local+official|official-fast-detectgpt",
  "cycles": 1,
  "mock_provider": false
}
```

Returns the same job envelope.

`GET /api/jobs/{job_id}`

Returns:

```json
{
  "job_id": "string",
  "kind": "detect|refine",
  "status": "queued|running|succeeded|failed",
  "created_at": "iso8601",
  "finished_at": "iso8601|null",
  "error": "string|null",
  "result": {}
}
```

## Result DTO

Detector-only result should expose:

- `summary.risk`
- `summary.consensus`
- `summary.disagreement`
- `detectors[]`
- `warnings[]`

Refinement result should expose:

- `original_text`
- `refined_text`
- `summary`
- `before`
- `after`
- `diagnostic_refinement`
- `preservation`
- `artifact_path`

## Cost Controls

- Default detector preset: `local`.
- Production feedback preset: `local+official`, but only if env is configured.
- Text length cap: default 4000 words or configurable by `ACADEMIC_ENGINE_WEB_MAX_WORDS`.
- Worker concurrency: default 1, configurable by `ACADEMIC_ENGINE_WEB_WORKERS`.
- Fast-DetectGPT endpoint should remain external to the web process; deploy/undeploy policy remains operational, not embedded in request handlers.

## Verification

- Run `python -m pytest`.
- Run focused web tests.
- Start local dev server with mock provider/local detectors and verify `/health`.
- Do not deploy publicly in this step unless separately requested.
