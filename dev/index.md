# Development Memory Index

Curated references only.

## Process

- [Local memory protocol](../AGENTS.md): required startup and Markdown memory rules.
- [Memory directory guide](README.md): directory purposes, naming, and index policy.

## Decisions

- [Use local Markdown memory](decisions/2026-06-02-1202--dev-memory--markdown-memory--decision.md): establishes `dev/` as the durable local memory system.
- [Use detector signals in Phase 1](decisions/2026-06-02-1206--academic-engine--detector-signal-runtime--decision.md): detector-risk signals are part of the CLI loop, while semantic preservation remains the hard gate.

## Current State

- [Initial memory setup handoff](handoffs/2026-06-02-1202--dev-memory--initial-setup--handoff.md): current status after bootstrapping the system.
- [Worker-ready academic engine architecture](plans/2026-06-02-1205--academic-engine--worker-ready-architecture--plan.md): Phase 1 plan and launch contract for a `gpt-5.5` worker with low reasoning effort.
- [Academic engine worker handoff](handoffs/2026-06-02-1206--academic-engine--worker-ready--handoff.md): current requirements and worker launch state after detector/DeepSeek clarifications.
- [Phase 1 implementation log](logs/2026-06-02-1237--academic-engine--phase-1-implementation--log.md): worker implementation summary and verification.
- [Phase 1 review fixes log](logs/2026-06-02-1241--academic-engine--phase-1-review-fixes--log.md): coordinator review fixes for citation extraction, safe final selection, `.env` loading, and tests.
- [CLI reporting loop log](logs/2026-06-02-1253--academic-engine--cli-reporting-loop--log.md): adds final-candidate, stop-reason, cycle summary, and non-disruptive-change reporting for the CLI loop.
- [Refinement loop verification log](logs/2026-06-02-1254--academic-engine--refinement-loop-verification--log.md): coordinator verification of worker patch, forced-cycle mock smoke, and artifact-write cleanup.
- [DeepSeek live smoke log](logs/2026-06-02-1307--academic-engine--deepseek-live-smoke--log.md): schema prompt/repair fixes and first successful live DeepSeek CLI run.
- [Local detector ensemble log](logs/2026-06-02-1459--academic-engine--local-detector-ensemble--log.md): worker implementation of lightweight local detector signals and optional HF adapter.
- [Local detector ensemble review log](logs/2026-06-02-1509--academic-engine--local-detector-ensemble-review--log.md): coordinator review, detector-set contract fix, close-utility selection tweak, and verification.
- [Sample detector comparison log](logs/2026-06-02-1559--academic-engine--sample-detector-comparison--log.md): synthetic sample before/after comparison using live DeepSeek and local detector ensemble.
- [Community detector integration log](logs/2026-06-02-1605--academic-engine--community-detectors--log.md): optional Binoculars, Ghostbuster, MAGE, and RADAR adapters with fallback behavior, stronger consensus weights, CLI selection, verification, and Binoculars install blocker.
- [Community detector review log](logs/2026-06-02-1644--academic-engine--community-detectors-review--log.md): Binoculars Python 3.11 smoke, community staging review, timeout fix, and mock prompt-leak fix.
- [RunPod Flash calibration plan](plans/2026-06-02-2023--academic-engine--runpod-flash-calibration--plan.md): scoped implementation plan for Flash teacher detectors and all-candidate calibration.
- [RunPod Flash calibration log](logs/2026-06-02-2023--academic-engine--runpod-flash-calibration--log.md): Flash detector provider, calibration CLI/artifact, endpoint scaffold, and verification.
- [RunPod GPU first call attempt log](logs/2026-06-02-2048--academic-engine--runpod-gpu-first-call-attempt--log.md): Flash endpoint build succeeded, deploy blocked pending explicit cloud/billing approval.
- [Flash detector reliability log](logs/2026-06-04-1102--academic-engine--flash-detector-reliability--log.md): stable Flash detector profile, health-check CLI, v7 endpoint id, and proxy/model-backed detector status.
- [RunPod cost control log](logs/2026-06-04-1117--academic-engine--runpod-cost-control--log.md): undeployed all active Flash endpoints, switched future endpoint config to 16GB GPU, and made stable Flash default RADAR-only.
- [Three model detector signals log](logs/2026-06-04-1120--academic-engine--three-model-detectors--log.md): stable Flash profile now uses RADAR, OpenAI RoBERTa detector, and Hello-SimpleAI ChatGPT RoBERTa detector.
- [Official detector stack calibration log](logs/2026-06-06-1131--academic-engine--official-detector-stack-calibration--log.md): official detector providers, wrappers, thesis calibration fixture, tiny Binoculars smoke, and official detector failure modes.
- [Official Flash autowire log](logs/2026-06-06-1137--academic-engine--official-flash-autowire--log.md): one-env RunPod routing for official Binoculars/Fast-DetectGPT, packaged endpoint wrappers, and dummy endpoint health verification.
- [Official GPU calibration handoff](handoffs/2026-06-06-1137--academic-engine--official-gpu-calibration--handoff.md): next-step state for deploying the cost-aware official detector endpoint and rerunning thesis calibration.
- [Official Flash predeploy log](logs/2026-06-06-1149--academic-engine--official-flash-predeploy--log.md): isolated official Flash app, successful slim build artifact, and packaging findings before any billable deploy.
- [Official Flash pause and undeploy log](logs/2026-06-06-1759--runpod-flash-official--pause-and-undeploy--log.md): endpoint `detect-fb` undeployed, latest bootstrap timeout status, and next resume steps.
- [Official Flash resume iteration log](logs/2026-06-06-1806--runpod-flash-official--resume-iteration--log.md): timeout/bootstrap fixes, Qwen Binoculars live success, thesis-text disclosure blocker, and final undeploy state.
- [Official Fast-DetectGPT calibration log](logs/2026-06-06-2050--runpod-flash-official--fast-detectgpt-calibration--log.md): cost-controlled RunPod calibration where Fast-DetectGPT GPT-Neo separated the thesis fixture and Binoculars Qwen did not.
- [Diagnostic refinement workflow log](logs/2026-06-07-1007--academic-engine--diagnostic-refinement-workflow--log.md): failure-mode guided refinement workflow, acceptance gating, artifact diagnostics, and local/mock verification.
- [Web prototype MVP plan](plans/2026-06-08-1205--web-prototype--detector-refinement-mvp--plan.md): first web/API layer for detector-only and refinement feedback workflows.
- [Web prototype MVP log](logs/2026-06-08-1230--web-prototype--detector-refinement-mvp--log.md): FastAPI job runner, static UI, DTO summaries, tests, and local HTTP smoke.
- [Curated web detector/humanizer plan](plans/2026-06-11-1718--web-prototype--curated-detector-humanizer-site--plan.md): refined web UI and Fast-DetectGPT-on-demand backend contract.
- [Curated web detector/humanizer log](logs/2026-06-11-1718--web-prototype--curated-detector-humanizer-site--log.md): polished static UI, focused Fast preset routing, health readiness metadata, and browser smoke verification.
- [Web prototype UI audit](audits/2026-06-11-1729--web-prototype-ui/audit.md): Product Design audit of the current detector/humanizer UI with screenshots, UX/accessibility risks, and redesign recommendations.
- [Audit-driven web redesign log](logs/2026-06-11-1739--web-prototype--audit-driven-redesign--log.md): guided diagnostic workspace redesign with public presets, recommendation-first results, advanced detector disclosure, and browser verification.
- [Remote endpoint policy log](logs/2026-06-11-2131--web-prototype--remote-endpoint-policy--log.md): backend policy, cache, rate-limit, concurrency, fallback, and health metadata for web Fast-DetectGPT endpoint usage.
- [Local detector ensemble plan](plans/2026-06-02-1459--academic-engine--local-detector-ensemble--plan.md): scoped implementation plan for lightweight local detector signals and optional HF adapter.
- [Community detector integration plan](plans/2026-06-02-1605--academic-engine--community-detectors--plan.md): scoped implementation plan for community detector adapters and verification.
- [Local detector ensemble log](logs/2026-06-02-1459--academic-engine--local-detector-ensemble--log.md): implementation summary, verification, and calibration limits for detector ensemble work.
