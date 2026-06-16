# RunPod Batch Detector Architecture Plan

## Goal

Implement a cost-first detector architecture for the academic refinement pipeline, suitable for a low-reasoning worker to execute in small, verifiable steps.

The target is not "more detector calls"; the target is a robust multi-signal evaluator that uses GPU only when it adds enough value to justify cost.

## Current Constraints

- Optimize for cost first.
- Do not deploy RunPod resources without explicit approval.
- Keep `workers=(0, 1)` for serverless GPU endpoints.
- Keep default GPU target small: start with `GpuGroup.AMPERE_16`; benchmark before considering 24GB.
- Avoid `AMPERE_80` unless a benchmark proves it is required.
- Treat the three RoBERTa-like detectors as one correlated supervised cluster, not three independent signals.
- Preserve citations, numbers, terminology, claims, and argument structure as hard gates.
- Do not optimize solely for detector score reduction; detector signals are diagnostics inside a quality and preservation reward.

## Existing Important State

- All previous RunPod Flash endpoints were undeployed.
- Flash endpoint config has been moved toward `academic-engine-detectors-small-v1`.
- Stable profile recently added:
  - `radar`
  - `openai_roberta`
  - `chatgpt_roberta`
- This stable profile must be reinterpreted as `roberta_cluster`, not as three independent detector votes.
- Binoculars proxy and Ghostbuster proxy are not acceptable as stable official signals unless improved/containerized.

## Target Architecture

Use a single RunPod batch endpoint.

The pipeline should send one request per scoring event:

- many candidate texts
- selected detector/profile
- request metadata

RunPod should return:

- per-text normalized signal scores
- per-detector raw results
- cluster-level aggregate scores
- timing and model-load telemetry
- detector errors without failing the whole batch

The pipeline should not call RunPod once per detector or once per candidate.

## Signal Model

### CPU Always-On Signals

Run locally before any GPU call:

- citation preservation
- numeric preservation
- terminology preservation
- semantic similarity or lexical overlap proxy
- stylometry:
  - sentence-length entropy
  - burstiness
  - lexical diversity
  - repetition
  - discourse-marker density
  - generic phrase density

These are cheap, always available, and should be used for prefiltering and guardrails.

### GPU Stable Signals

Stable GPU profile should expose one cluster:

```text
roberta_cluster:
  members:
    - radar
    - openai_roberta
    - chatgpt_roberta
  role: correlated supervised baseline
  weight: low-medium
```

Cluster output should include:

- member scores
- mean score
- median score
- disagreement
- unavailable member list

The scoring layer should consume `roberta_cluster_score`, not count each member independently.

### GPU Calibration Signals

Calibration profile should add more orthogonal detector families:

```text
calibration:
  - roberta_cluster
  - official_or_modern_binoculars
  - fast_detectgpt_like
  - ghostbuster_official_if_containerized
```

These signals are for calibration and research batches, not every production request.

### LLM Judge Signal

Use DeepSeek via API, not RunPod GPU, for rubric-style judging:

- naturalness
- specificity
- register consistency
- semantic preservation
- factual consistency
- genericity or assistant-like phrasing

This should be a quality guardrail and reward component, not a detector replacement.

## RunPod Endpoint Contract

Endpoint operations:

- `health`
- `model_inventory`
- `score_batch`
- `warmup` only when explicitly requested for benchmarking

Request fields for `score_batch`:

- `operation`
- `profile`
- `texts`
- `detectors` optional override
- `max_length`
- `request_id`
- `return_raw`

Each text item:

- `id`
- `text`
- optional `source`
- optional `candidate_id`

Response fields:

- `request_id`
- `profile`
- `device`
- `results`
- `timing`
- `loaded_models`
- `errors`

Each result:

- `id`
- `signals`
- `raw_detector_results`
- `detector_disagreement`
- `artificiality_risk`
- `warnings`

Timing must include:

- total endpoint time
- model load time per model
- inference time per detector
- batch size

## Pipeline Contract

Add a RunPod batch provider abstraction.

Expected pipeline flow:

1. Generate candidates with DeepSeek.
2. Run local CPU preservation and stylometry checks.
3. Filter obviously invalid candidates locally.
4. If GPU is enabled for the current mode, send all surviving candidates in one `score_batch`.
5. Merge GPU signals with local signals.
6. Rank candidates using composite reward:
   - quality preservation
   - naturalness
   - specificity
   - low artificiality risk
   - low distortion
7. Select final candidate only if hard gates pass.

## Cost Controls

Mandatory:

- one batch call per pipeline scoring stage
- no detector-by-detector API loop
- no candidate-by-candidate API loop
- `workers=(0, 1)`
- `idle_timeout` between 30 and 45 seconds during experiments
- explicit deploy approval
- explicit benchmark approval
- timeout per RunPod request
- circuit breaker after repeated RunPod failures
- local fallback when RunPod unavailable

Recommended:

- use `stable_cpu` mode by default during development
- use GPU only in `calibration` and explicit `flash` modes
- cache health checks locally with a TTL
- benchmark batch sizes 1, 5, 10, 20 before broader use

## Implementation Phases For Low-Reasoning Worker

### Phase 0: Orientation

Worker must read:

- `AGENTS.md`
- `dev/index.md`
- this plan
- latest RunPod cost-control and detector logs

Worker must not deploy or call RunPod in this phase.

Deliverable:

- brief note in working memory or final response listing files inspected.

### Phase 1: Detector Registry

Create a registry layer that defines detector metadata:

- name
- family
- profile
- model name
- implementation kind
- expected device
- cost class
- cluster membership
- default weight
- known status

Represent the three RoBERTa-like models as members of `roberta_cluster`.

Deliverables:

- registry module or config object
- tests for profile expansion
- tests proving `stable` emits `roberta_cluster`, not three independent score weights

### Phase 2: Batch Result Schema

Add internal schemas for:

- batch request
- batch response
- detector signal
- clustered signal
- timing telemetry
- partial failure

Deliverables:

- Pydantic models or equivalent existing schema style
- serialization tests
- backward compatibility with existing single-detector result where needed

### Phase 3: RunPod Batch Client

Replace or extend the Flash detector provider with a batch-capable client.

Required behavior:

- one request for many texts
- endpoint id from env/config
- no secrets printed
- timeout handling
- partial failure handling
- clear unavailable result when RunPod is not configured
- local fallback path

Deliverables:

- batch client abstraction
- unit tests with mocked endpoint response
- tests for timeout and malformed response

### Phase 4: Pipeline Integration

Modify candidate scoring so teacher/GPU detectors run as one batch over candidate lists.

Required behavior:

- local detectors run first
- invalid candidates are not sent to GPU unless calibration mode explicitly requests all
- GPU results are merged back by candidate id
- final selected candidate has complete audit details

Deliverables:

- pipeline batch scoring path
- tests proving one batch call for multiple candidates
- tests proving final report includes cluster and timing metadata

### Phase 5: Endpoint Batch Implementation

Update `scripts/runpod_flash/detectors_endpoint.py` to support:

- `operation=health`
- `operation=model_inventory`
- `operation=score_batch`
- lazy model loading
- model cache
- per-detector timing
- per-text results
- partial detector failure

Do not deploy during this phase.

Deliverables:

- endpoint script compiles
- local import/compile smoke
- pure unit tests for helper functions where practical

### Phase 6: Composite Reward

Refactor scoring to consume signal families:

- `supervised_classifier_cluster`
- `stylometry`
- `llm_quality_judge`
- optional `zero_shot_lm_signal`
- optional `feature_based_signal`

Do not over-weight correlated RoBERTa members.

Deliverables:

- scoring changes
- regression tests showing RoBERTa cluster counts as one signal
- regression tests preserving hard gates over detector improvement

### Phase 7: Offline Verification

Run:

- full unit tests
- mock pipeline run
- mock calibration artifact
- no RunPod calls

Deliverables:

- test summary
- implementation log
- no endpoint id introduced into `.env`

### Phase 8: Controlled Deployment Plan

Only after explicit approval:

1. Build Flash artifact.
2. Deploy `academic-engine-detectors-small-v1` on `AMPERE_16`.
3. Run `health`.
4. Run `model_inventory`.
5. Run one `score_batch` with 1 text.
6. If successful, benchmark 5 and 10 texts.
7. Stop if latency, memory, or cost is unacceptable.
8. Undeploy immediately if benchmark fails.

Deliverables:

- benchmark artifact
- cost/latency summary
- recommendation: keep 16GB, move to 24GB, or stay CPU/local

## Acceptance Criteria

Implementation is acceptable when:

- Pipeline can score multiple candidates with one RunPod request.
- RoBERTa-like detectors are clustered as one correlated signal.
- GPU is not required for default local development.
- RunPod unavailable state does not break the pipeline.
- No RunPod resources are created without explicit approval.
- Reports include timing, model names, implementation kind, and errors.
- Hard preservation gates override detector score improvements.
- Full test suite passes.

## Worker Launch Instruction

Use a model with reasoning effort low.

Work in small phases. After each phase:

- run focused tests
- report changed files
- stop before any RunPod deploy or billable call

Do not start a worker until explicitly instructed.
