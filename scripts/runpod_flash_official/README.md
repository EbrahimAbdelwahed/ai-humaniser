# Official Detector Flash App

Cost-aware RunPod Flash app for official detector runtime experiments.

This app is intentionally packaged as a code-only artifact. Heavy GPU/runtime
dependencies and official detector repositories must come from the RunPod base
image, a prebuilt image, a mounted volume, or an explicitly enabled bootstrap
step. This keeps uploads small and makes dependency failures visible instead of
hiding them in a large Flash archive.

## Endpoint

- Source: `official_detectors_endpoint.py`
- Name: `academic-engine-official-detectors-v1`
- GPU: `ADA_24`, `AMPERE_24`, or `AMPERE_16`
- Workers: `(0, 1)`
- Idle timeout: `30s`
- Scale: `0..1` worker
- Supports:
  - `official_binoculars`
  - `official_fast_detectgpt`
- Documents but does not execute:
  - `official_ghostbuster`

## Local Build Preflight

Use the code-only build. It keeps the artifact under the RunPod Flash 500MB limit by excluding detector/runtime packages from the upload.

```sh
cd scripts/runpod_flash_official
flash build --no-deps --exclude torch,torchvision,torchaudio,numpy,scipy,scikit-learn,sklearn,transformers,accelerate,sentencepiece,protobuf
```

Verified result on 2026-06-06:

- archive: `.flash/artifact.tar.gz`
- size: about `0.2M`
- manifest resource: `detect`
- handler: `handler_detect.py`
- GPU ids: `ADA_24,AMPERE_24,AMPERE_16`

The code-only artifact intentionally does not bundle `torch`, `transformers`, `numpy`, or detector repositories. The active iterative profile uses 24GB GPUs with smaller same-tokenizer model pairs. The official Falcon-7B/Falcon-7B-Instruct Binoculars default was observed to OOM on 24GB and should be treated as a 48GB calibration profile. After deploy, the first health/model test must verify whether the Flash base image already provides the required runtime packages. If not, use controlled runtime bootstrap for calibration or switch to a prebuilt Docker image/persistent volume once the required runtime is known.

For 24GB iterative calibration, set:

```text
ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_OBSERVER_MODEL=Qwen/Qwen2.5-1.5B
ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_PERFORMER_MODEL=Qwen/Qwen2.5-1.5B-Instruct
```

## Runtime Bootstrap

Remote bootstrap is optional and controlled. The endpoint enables it by default
for live calibration calls so code-only deployments can install missing official
detector dependencies inside the disposable worker. Disable it for local tests or
strict dependency checks with `runtime_bootstrap=false` in the request payload or
`OFFICIAL_DETECTOR_RUNTIME_BOOTSTRAP=0` in the endpoint environment.

```text
OFFICIAL_DETECTOR_RUNTIME_BOOTSTRAP=1
OFFICIAL_DETECTOR_BOOTSTRAP_ROOT=/tmp/academic_engine_official_detectors
OFFICIAL_DETECTOR_INSTALL_REQUIREMENTS=0
BINOCULARS_REPO=/workspace/Binoculars
FAST_DETECTGPT_REPO=/workspace/fast-detect-gpt
```

Bootstrap may install missing Python packages or clone official detector repos
into the remote runtime. It must not be required for local tests, and it must not
run implicitly during `flash build`.

If bootstrap is disabled, unavailable dependencies should fail explicitly:

- missing wrapper: `failure_mode=wrapper_missing`
- missing Python dependency such as `torch`: `failure_mode=dependency_missing`
- missing Fast-DetectGPT repo/assets: `failure_mode=model_assets_missing`
- Fast-DetectGPT defaults to the calibrated `gpt-neo-2.7B/gpt-neo-2.7B` pair for 16/24GB calibration. Set `ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_SAMPLING_MODEL` and `ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_SCORING_MODEL` to override.
- missing Ghostbuster OpenAI access: `failure_mode=api_key_missing`

Prefer a prebuilt image or persistent volume once the required official runtime
is known. Treat runtime bootstrap as a controlled calibration aid, not as the
stable production deployment path.

## Deploy

Do not deploy without explicit billing approval.

```sh
cd scripts/runpod_flash_official
flash deploy --no-deps --exclude torch,torchvision,torchaudio,numpy,scipy,scikit-learn,sklearn,transformers,accelerate,sentencepiece,protobuf
```

After deploy, set:

```text
ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=<endpoint-id>
ACADEMIC_ENGINE_DETECTORS=local+official
```

## Post-Deploy Checks

```sh
python -m academic_engine.cli detector-health \
  --detectors official \
  -o experiments/thesis_calibration_2026_06_06/results/detector_health.official_flash.live.json
```

Then run thesis calibration:

```sh
python -m academic_engine.cli raw-audit \
  experiments/thesis_calibration_2026_06_06/samples/capitolo2_ai_generated.txt \
  experiments/thesis_calibration_2026_06_06/samples/introduzione_capitolo1_human_first_paragraph.txt \
  experiments/thesis_calibration_2026_06_06/samples/potere_persuasivo_musica_ai_generated.txt \
  -o experiments/thesis_calibration_2026_06_06/results/raw_audit.local_official_flash.live.json \
  --detectors local+official
```
