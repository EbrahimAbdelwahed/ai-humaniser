# Plan: Worker-Ready Architecture For Academic Writing Engine

## Goal

Define enough architecture for a `worker` agent using model `gpt-5.5` with reasoning effort `low` to start implementation and iterate until the Phase 1 prototype is complete.

The project goal is an academic writing refinement system that improves clarity, scholarly voice, cohesion, precision, and detector false-positive robustness while preserving meaning, factual claims, disciplinary terminology, citations, and argument structure.

## Model Contract

OpenAI model docs list `gpt-5.5` as the model id and `low` as a supported reasoning effort, so treat the user shorthand `gpt-5.5-low` as:

```text
model = gpt-5.5
reasoning_effort = low
agent_type = worker
```

Do not treat `gpt-5.5-low` as a separate model id unless the local runtime explicitly exposes it that way.

## Product Direction

After the engine prototype, the final product should become a web app.

Architect Phase 1 as an engine/library plus CLI so the same core can later be wrapped by:

- a backend API
- a web frontend
- queued rewrite jobs
- detector audit dashboards
- private per-user run storage

Do not build the web app in Phase 1.

## Core Principle

The system optimizes student writing quality and detector false-positive robustness.

Detector signals are allowed in Phase 1 as an operational signal during scoring, ranking, and refinement. They must not override hard preservation constraints:

- no invented facts
- no invented citations
- no altered scientific or disciplinary claims
- no omitted arguments
- no unsupported conclusions
- no disruptive changes to the student's intended meaning

The product should not promise guaranteed undetectability. The practical target is: well-written academic prose with low detector-risk signals and no disruptive semantic changes.

## Runtime LLM Provider

Use DeepSeek V4 Flash via API for text generation and LLM-judged analysis/scoring.

Official DeepSeek API docs list the model id as:

```text
deepseek-v4-flash
```

The implementation worker may itself run as `gpt-5.5` with low reasoning effort, but the product runtime should call DeepSeek for generation.

Environment configuration:

```text
DEEPSEEK_API_KEY=<required>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

Use an OpenAI-compatible client abstraction so the model provider can be swapped later without rewriting the pipeline.

## Recommended Stack

Use Python for Phase 1.

Rationale:

- best ecosystem fit for NLP evaluation, NLI, BERTScore, sentence analysis, and future dataset work
- straightforward CLI-first prototype
- easy transition into a service layer later
- avoids premature frontend/API decisions before the engine behavior is validated

Initial shape:

```text
ai_humaniser/
  pyproject.toml
  src/academic_engine/
    __init__.py
    cli.py
    config.py
    llm.py
    pipeline.py
    schemas.py
    prompts/
      semantic_analysis.md
      academic_profile.md
      candidate_generation.md
      candidate_scoring.md
      refinement.md
      revision_report.md
  tests/
    fixtures/
    test_schemas.py
    test_pipeline_contract.py
    test_scoring.py
  examples/
    input/
    output/
  runs/
    .gitkeep
  dev/
```

## Domain Pipeline

Phase 1 should be a prompt-based inference pipeline, not training.

Pipeline:

```text
InputText
  -> InputNormalization
  -> DeepSemanticAnalysis
  -> AcademicContextAnalysis
  -> MultiStrategyCandidateGeneration
  -> DetectorSignalAnalysis
  -> AcademicQualityScoring
  -> CandidateRanking
  -> IterativeRefinement
  -> FinalSelection
  -> RevisionReport
  -> ExperimentSummary
```

### 1. Input Normalization

Responsibilities:

- preserve original text exactly in run artifacts
- detect language, approximate document type, and paragraph boundaries
- reject empty or obviously invalid input
- warn on unsupported inputs rather than silently producing output

### 2. Deep Semantic Analysis

Output: `SemanticRepresentation`

Minimum fields:

- claims
- entities
- relations
- disciplinary_terms
- citations_or_references
- exact_citation_spans
- numeric_values
- argument_structure
- uncertainty_markers
- non_negotiable_preservation_items

The worker should implement this as a structured LLM call first. Later, deterministic NLP checks can be added.

### 3. Academic Context Analysis

Output: `AcademicProfile`

Minimum fields:

- discipline
- subdiscipline
- document_type
- audience
- writing_level
- author_needs
- style_constraints

The module should infer when metadata is missing, but mark inferred fields as inferred.

### 4. Candidate Generation

Output: list of `CandidateRevision`

Generate 5 to 8 candidates using explicit strategies:

- conservative_academic
- natural_scholarly
- enhanced_clarity
- structural_optimization
- stylistic_maturation
- non_native_refinement
- precision_oriented

Every candidate must include:

- rewritten text
- strategy
- intended improvements
- explicit preservation notes
- risk flags if meaning may have shifted

Candidates should preserve citations exactly. In Phase 1, citation handling means extraction, protection, and drift detection. Do not normalize citation style, invent missing citation metadata, reformat bibliography entries, or add references.

### 5. Detector Signal Analysis

Output: list of `DetectorResult`

Detector signals are part of the Phase 1 CLI. The goal is to measure and reduce false-positive-prone patterns while preserving academic quality.

Implement a provider interface:

```text
DetectorProvider.analyze(text) -> DetectorResult
```

Minimum `DetectorResult` fields:

- provider_name
- provider_kind: `api`, `browser`, `manual`, or `heuristic`
- available
- label
- score
- confidence
- raw_result
- error
- checked_at
- input_hash

Phase 1 should support:

- a local heuristic detector-risk analyzer so tests and demos work without external accounts
- configurable external detector providers when API keys or supported access methods are available
- run artifacts that record detector results per candidate and per refinement cycle

For mainstream external detectors, later work should perform a current web search and choose the first 10 mainstream systems with usable access paths. Prefer official APIs or documented integrations. Do not depend on brittle or unauthorized scraping as the default architecture.

### 6. Academic Quality Scoring

Output: `ScoreCard`

Use the weighted score from the project goal:

```text
0.28 semantic_fidelity
0.22 factual_consistency
0.15 academic_authenticity
0.12 logical_flow_cohesion
0.10 academic_tone_quality
0.08 clarity_readability
0.05 stylistic_sophistication
```

Also compute naturalness diagnostics:

- syntactic variation
- lexical diversity
- discourse flexibility
- repetitive structure risk
- generic LLM pattern risk

Scoring can be LLM-judged in Phase 1, but responses must be structured and auditable.

Add detector-risk scoring as a separate dimension:

- detector_risk_score
- detector_label_consensus
- detector_disagreement
- false_positive_risk_notes

Suggested Phase 1 selection utility:

```text
candidate_utility =
  0.45 preservation_safety
  0.25 academic_quality
  0.20 detector_false_positive_robustness
  0.10 non_disruptive_edit_score
```

The utility weights can be tuned empirically, but `preservation_safety` must remain the first gate.

### 7. Candidate Ranking

Ranking should prioritize hard constraints first:

1. no invented facts
2. no altered claims
3. no invented citations
4. no omitted important arguments
5. no unsupported conclusions

Only candidates passing constraint checks should be ranked by candidate utility.

### 8. Iterative Refinement

Refinement loop:

1. take top 1 to 2 candidates
2. critique against semantic representation and academic profile
3. run detector signal analysis
4. identify detector-risk patterns that can be improved without semantic disruption
5. generate improved revision
6. rescore quality and detector signals
7. stop after configured cycles

Stop conditions:

- candidate passes hard constraints, exceeds configured academic quality threshold, and reaches configured detector-risk target
- maximum refinement cycles reached
- semantic risk is too high, in which case return best safe candidate with warnings
- detector target cannot be improved without disruptive changes, in which case preserve meaning and return warnings

Default maximum:

- 2 refinement cycles for normal CLI runs
- configurable higher limit for experiments

### 9. Revision Report

Output format:

- refined_text
- major_revisions
- semantic_preservation_analysis
- academic_quality_analysis
- style_analysis
- detector_signal_analysis
- warnings
- optional_detector_audit

### 10. Experiment Harness

The CLI should support single-run rewriting and repeatable experiments over fixtures.

Experiment mode should:

- run the pipeline over a fixture directory
- record per-fixture detector risk before and after rewriting
- record edit distance or another non-disruptive-change proxy
- record preservation warnings and hard-constraint failures
- record final academic quality and utility scores
- produce a JSON summary suitable for comparing prompt and scoring changes

The goal is to determine whether prompt-based instructions are enough to make the tool useful before training or web app work begins.

## Data Contracts

Use Pydantic models or equivalent typed schemas.

Core schemas:

- `RewriteJob`
- `RunState`
- `AcademicProfile`
- `SemanticRepresentation`
- `CandidateRevision`
- `DetectorResult`
- `ScoreCard`
- `RankedCandidate`
- `RefinementCycle`
- `RevisionReport`
- `PipelineResult`
- `ExperimentSummary`

All LLM responses should be validated against schemas. Invalid responses should be retried once with a repair prompt, then fail loudly with a useful error.

## Worker Control Loop

The worker should not try to build the entire future product at once. It should iterate by completing small, verifiable slices.

Loop:

```text
read AGENTS.md and dev/index.md
read this plan
inspect current repo state
choose the next smallest implementation slice
create or update a dev/plans task note if the slice is complex
implement the slice
run focused verification
write dev/logs entry
update handoff if work is incomplete
repeat until Phase 1 acceptance criteria pass
```

The worker must preserve unrelated changes and follow the local memory protocol.

## Worker Launch Prompt

Use this prompt when starting the worker:

```text
Read AGENTS.md, dev/index.md, and dev/plans/2026-06-02-1205--academic-engine--worker-ready-architecture--plan.md.

Implement Phase 1 only: a Python CLI-first prompt-based academic writing refinement engine.

Use model gpt-5.5 with reasoning effort low for your own agent setting. For product text generation and LLM-judged pipeline stages, use the DeepSeek API model deepseek-v4-flash configured from environment variables. Build the pipeline, schemas, prompt templates, detector signal analysis, run artifacts, tests, and example workflow needed to process an input text and produce a validated revision report.

The CLI must already use detector signals during scoring, ranking, and refinement. Optimize for well-written academic prose with low detector false-positive risk, while preserving citations, facts, claims, terminology, and argument structure. Do not claim guaranteed undetectability.

Iterate autonomously until the Phase 1 acceptance criteria in the plan pass. Keep changes scoped, write local dev memory logs, and do not revert user changes.
```

Tool-level launch shape:

```text
agent_type = worker
model = gpt-5.5
reasoning_effort = low
message = <Worker Launch Prompt>
```

## Phase 1 Acceptance Criteria

The worker is done when all of these are true:

- repo has a Python package skeleton with installable project metadata
- CLI accepts an input text file and writes a structured JSON result
- pipeline executes all core stages in order
- schemas validate all stage outputs
- candidate generation supports at least 5 strategies
- product runtime uses `deepseek-v4-flash` through a provider abstraction
- DeepSeek API key and model are configured through environment variables
- citations are extracted/protected and preserved exactly unless the user explicitly asks otherwise
- detector signal analysis runs in the CLI through at least one local heuristic provider
- external detector provider interfaces are configurable for later mainstream detector integrations
- scoring produces weighted composite scores and hard-constraint flags
- ranking includes detector false-positive robustness as a meaningful signal
- refinement supports 1 to 2 configured cycles
- final report includes refined text and analysis sections
- final report includes detector signal analysis
- tests cover schema validation, scoring math, and pipeline contract
- example input and output are present
- experiment mode can run multiple fixtures and summarize before/after detector-risk, quality, and non-disruptive-change metrics
- fixture examples cover high-student-volume domains
- run artifacts are saved under `runs/`
- `.env` and private run artifacts are not exposed publicly or committed
- no module claims guaranteed undetectability
- dev log documents what was implemented and how it was verified

## Phase 2 And Later

Do not start these until Phase 1 is stable:

- dataset construction
- BERTScore and NLI integrations
- detector audit dashboard
- web UI
- service API
- supervised fine-tuning
- preference optimization
- reward modeling

## Open Questions

Resolved product questions:

- final product direction: web app after the CLI engine prototype
- prioritized domains: high-student-volume fields, including political science, communication/media studies, psychology, economics/business, medicine/health sciences, chemistry, biology/life sciences, education, sociology, engineering, and computer science
- citation policy: preserve user-provided citations exactly; do not parse for style normalization in Phase 1
- privacy baseline: avoid public exposure, keep `.env` private, and do not commit user manuscript run artifacts
- detector direction: use mainstream detector systems later, selected by a current web search and usable access paths

Remaining questions that do not block the worker from starting Phase 1:

- Which detector services will have usable API keys or acceptable access paths?
- What detector-risk target should count as "good enough" for early experiments?
- Should the web app backend be Python/FastAPI, Next.js API routes, or another stack after Phase 1?
