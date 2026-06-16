# AI Humaniser Academic Engine

Phase 1 is a Python CLI-first prototype for academic writing refinement. It uses a provider abstraction for DeepSeek `deepseek-v4-flash` and falls back to a deterministic mock provider when no API key is configured or `--mock-provider` is passed.

The engine optimizes academic quality and detector false-positive robustness while preserving citations, facts, claims, terminology, numeric values, and argument structure as hard gates. It does not claim guaranteed undetectability.

```sh
academic-engine run examples/input/political_science.txt -o examples/output/political_science.result.json --mock-provider
academic-engine experiment tests/fixtures -o examples/output/experiment-summary.json --mock-provider
```

Detector diagnostics default to a lightweight local ensemble with no downloads or API calls. To also try a locally cached HuggingFace detector, pass `--include-hf-detector` or `--detectors local+hf`; if `transformers` or the model files are unavailable, the run continues and records that detector as unavailable.

Community detector adapters are available with `--detectors community`, `--detectors local+community`, or `--detectors all`. The adapters are lazy and sequential by default. They target:

- Binoculars: official `ahans30/Binoculars` import when installed, or `ACADEMIC_ENGINE_BINOCULARS_CLI`.
- Ghostbuster: local wrapper command via `ACADEMIC_ENGINE_GHOSTBUSTER_CLI` after installing `vivek3141/ghostbuster`.
- MAGE: local wrapper command via `ACADEMIC_ENGINE_MAGE_CLI` after installing `yafuly/MAGE`.
- RADAR: local wrapper command via `ACADEMIC_ENGINE_RADAR_CLI` after installing official IBM/RADAR resources.

Wrapper commands read the text from stdin and should print either a numeric AI-risk score in `0..1` or JSON such as `{"score": 0.73, "confidence": 0.82, "label": "elevated_risk"}`. Missing community dependencies do not block the pipeline; they appear in the report as unavailable detector signals. Community detector scores receive stronger consensus weights than lightweight heuristics when available, but hard gates on citations, numbers, facts, claims, terminology, and argument structure still dominate final selection.

Optional bounded parallel detector execution is available for short local commands:

```sh
academic-engine run examples/input/political_science.txt -o examples/output/political_science.community.result.json --mock-provider --detectors local+community
academic-engine run examples/input/political_science.txt -o examples/output/political_science.all.result.json --mock-provider --detectors all --detector-execution parallel --detector-concurrency 2
```

For `local+community` and `all`, expensive community detectors are staged by default: the local ensemble ranks all generated candidates first, then community detectors run on the top 2 candidates plus later refinement/final candidates. Adjust with `--community-candidate-limit` or `ACADEMIC_ENGINE_COMMUNITY_CANDIDATE_LIMIT`.

RunPod Flash teacher detectors are available with `--detectors flash`, `local+flash`, `community+flash`, or `all`. Configure `RUNPOD_API_KEY`, `ACADEMIC_ENGINE_FLASH_DETECTORS=binoculars,ghostbuster,mage,radar`, and either a shared `ACADEMIC_ENGINE_FLASH_ENDPOINT_ID` or detector-specific endpoint ids. Missing SDK, API key, or endpoint configuration is recorded as unavailable and does not block offline tests.

Calibration/research mode audits every generated/refined candidate with configured teacher detectors instead of staging only top-K:

```sh
academic-engine calibrate examples/input/political_science.txt -o examples/output/political_science.calibration.json --mock-provider --detectors local+flash
```

Flash endpoint scaffolding lives in `scripts/runpod_flash/`. Test locally from that directory with `flash run`; deploy only when ready to call actual RunPod GPU/serverless resources.

## Web prototype

The first feedback prototype exposes the same engine through a small FastAPI app:

```sh
pip install -e ".[web]"
academic-engine-web
```

Open `http://127.0.0.1:8000`.

The UI has two modes:

- `Detector`: scores pasted text with the selected detector preset.
- `Refine`: scores the pasted text, runs bounded diagnostic refinement, then reports before/after detector and preservation signals.

Useful environment controls:

```sh
ACADEMIC_ENGINE_WEB_MAX_WORDS=4000
ACADEMIC_ENGINE_WEB_WORKERS=1
ACADEMIC_ENGINE_WEB_HOST=127.0.0.1
ACADEMIC_ENGINE_WEB_PORT=8000
```

The default detector preset is local-only. `local+fast-detectgpt` adds only the official Fast-DetectGPT route to the local ensemble, while `official-fast-detectgpt` runs that remote signal alone. If RunPod or the endpoint id is missing, Fast-DetectGPT is reported as unavailable instead of crashing the request.

## Deploy on Vercel

This repository includes a Vercel Python entrypoint at `api/index.py`, `requirements.txt`, and `vercel.json`. Vercel hosts the FastAPI app and static UI; Fast-DetectGPT should stay on an external GPU endpoint such as the existing RunPod Flash official detector endpoint.

Deploy from the repository root:

```sh
vercel
vercel --prod
```

Set production environment variables in Vercel before using the Fast-DetectGPT presets:

```sh
vercel env add DEEPSEEK_API_KEY production
vercel env add ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID production
vercel env add RUNPOD_API_KEY production
vercel env add ACADEMIC_ENGINE_ENABLE_REMOTE_DETECTORS production
vercel env add ACADEMIC_ENGINE_WEB_INLINE_JOBS production
```

Recommended values:

```sh
ACADEMIC_ENGINE_ENABLE_REMOTE_DETECTORS=true
ACADEMIC_ENGINE_WEB_INLINE_JOBS=true
ACADEMIC_ENGINE_WEB_WORKERS=1
ACADEMIC_ENGINE_REMOTE_MAX_WORDS=1200
ACADEMIC_ENGINE_REMOTE_DAILY_LIMIT=100
ACADEMIC_ENGINE_REMOTE_PER_IP_DAILY_LIMIT=5
ACADEMIC_ENGINE_REMOTE_MIN_INTERVAL_SECONDS=10
ACADEMIC_ENGINE_REMOTE_MAX_CONCURRENT_JOBS=1
ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS=55
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`ACADEMIC_ENGINE_WEB_INLINE_JOBS` defaults to true when Vercel sets `VERCEL=1`. Inline jobs avoid relying on background in-memory workers between serverless requests. `DEEPSEEK_API_KEY` is required for real text regeneration/refinement in production. Without it, the app falls back to the deterministic mock provider, which is useful for interface testing but is not an LLM rewrite.

After deployment, check:

```sh
curl https://<your-project>.vercel.app/health
```

`official_fast_detectgpt.configured` should be `true` when both `ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID` and the required RunPod credentials are available to the Vercel function.
