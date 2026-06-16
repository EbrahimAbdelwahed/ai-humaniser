from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from academic_engine.candidate_audit import build_excluded_candidate_audit
from academic_engine.config import EngineConfig
from academic_engine.detectors import DetectorProvider, detector_providers_from_config
from academic_engine.llm import LLMProvider, provider_from_config
from academic_engine.refinement_diagnostics import (
    build_refinement_diagnostics,
    render_refinement_prompt_context,
    targeted_diagnostic_improvement,
)
from academic_engine.schemas import (
    AcademicProfile,
    CandidateRevision,
    ExperimentFixtureResult,
    ExperimentSummary,
    NormalizedInput,
    PipelineResult,
    RankedCandidate,
    RefinementCycle,
    RevisionReport,
    SemanticRepresentation,
    Strategy,
)
from academic_engine.scoring import detector_consensus, non_disruptive_change_score, score_candidate
from academic_engine.utils import extract_citations, extract_numbers, sentence_split


def is_teacher_detector(provider: DetectorProvider) -> bool:
    return (
        provider.provider_name.startswith("community_")
        or provider.provider_name.startswith("flash_")
        or provider.provider_name.startswith("official_")
    )


GENERATION_STRATEGIES: tuple[Strategy, ...] = (
    Strategy.conservative_academic,
    Strategy.natural_scholarly,
    Strategy.enhanced_clarity,
    Strategy.structural_optimization,
    Strategy.stylistic_maturation,
    Strategy.non_native_refinement,
    Strategy.precision_oriented,
)


class AcademicRewritePipeline:
    def __init__(
        self,
        config: EngineConfig | None = None,
        llm_provider: LLMProvider | None = None,
        detector_providers: list[DetectorProvider] | None = None,
    ) -> None:
        self.config = config or EngineConfig.from_env()
        self.llm = llm_provider or provider_from_config(self.config)
        self.detectors = detector_providers or detector_providers_from_config(self.config)
        self.config.runs_dir.mkdir(parents=True, exist_ok=True)

    def run_text(self, text: str, *, input_path: str | None = None, write_artifact: bool = True) -> PipelineResult:
        run_id = uuid.uuid4().hex[:12]
        normalized = self.normalize(text)
        semantic = self.semantic_analysis(normalized.normalized_text)
        profile = self.academic_context(normalized.normalized_text)
        candidates = self.generate_candidates(normalized.normalized_text)
        ranked = self.rank_candidates(normalized.original_text, candidates, semantic)
        cycles = self.refine(normalized.original_text, ranked, semantic)
        selected, selected_score, selected_detectors = self.select_final_candidate(ranked, cycles, normalized.original_text, semantic)
        selected_score, selected_detectors = self.ensure_final_community_signals(
            selected=selected,
            score=selected_score,
            detectors=selected_detectors,
            original_text=normalized.original_text,
            semantic=semantic,
        )
        if selected_score.hard_constraint_failures:
            selected, selected_score, selected_detectors = self.preservation_fallback(normalized.original_text, semantic)
        report = self.final_report(selected, selected_score, selected_detectors, ranked, cycles, normalized, semantic, profile)
        result = PipelineResult(
            run_id=run_id,
            input_path=input_path,
            normalized_input=normalized,
            semantic_representation=semantic,
            academic_profile=profile,
            candidates=candidates,
            ranked_candidates=ranked,
            refinement_cycles=cycles,
            final_report=report,
        )
        if write_artifact:
            artifact = self.config.runs_dir / f"{run_id}--pipeline-result.json"
            result.artifact_path = str(artifact)
            artifact.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    def normalize(self, text: str) -> NormalizedInput:
        if not text.strip():
            raise ValueError("input text is empty")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
        warnings = []
        if len(normalized.split()) < 25:
            warnings.append("Input is short; academic context and detector signals may be unstable.")
        return NormalizedInput(
            original_text=text,
            normalized_text=normalized,
            language="en",
            document_type="essay",
            paragraphs=paragraphs or [normalized],
            warnings=warnings,
        )

    def semantic_analysis(self, text: str) -> SemanticRepresentation:
        system = self.schema_prompt("SemanticRepresentation")
        user = self.schema_user(text)
        data = self.complete_json_with_repair(system=system, user=user, schema_name="SemanticRepresentation")
        semantic = self.validate_payload(
            data=data,
            schema_name="SemanticRepresentation",
            system=system,
            user=user,
            validator=SemanticRepresentation.model_validate,
        )
        deterministic_citations = extract_citations(text)
        deterministic_numbers = extract_numbers(text)
        semantic.exact_citation_spans = sorted(set(semantic.exact_citation_spans + deterministic_citations), key=text.find)
        semantic.citations_or_references = sorted(set(semantic.citations_or_references + deterministic_citations), key=text.find)
        semantic.numeric_values = sorted(set(semantic.numeric_values + deterministic_numbers), key=text.find)
        semantic.non_negotiable_preservation_items = sorted(
            set(semantic.non_negotiable_preservation_items + deterministic_citations + deterministic_numbers),
            key=lambda item: text.find(item) if item in text else 10**9,
        )
        return semantic

    def academic_context(self, text: str) -> AcademicProfile:
        system = self.schema_prompt("AcademicProfile")
        user = self.schema_user(text)
        data = self.complete_json_with_repair(system=system, user=user, schema_name="AcademicProfile")
        return self.validate_payload(
            data=data,
            schema_name="AcademicProfile",
            system=system,
            user=user,
            validator=AcademicProfile.model_validate,
        )

    def generate_candidates(self, text: str) -> list[CandidateRevision]:
        tasks = [
            (index, strategy)
            for index, strategy in enumerate(GENERATION_STRATEGIES, start=1)
        ]
        if self.config.candidate_generation_concurrency > 1:
            with ThreadPoolExecutor(max_workers=self.config.candidate_generation_concurrency) as executor:
                candidates = list(executor.map(lambda task: self.generate_candidate(text, task[0], task[1]), tasks))
        else:
            candidates = [self.generate_candidate(text, index, strategy) for index, strategy in tasks]
        return candidates

    def generate_candidate(self, text: str, index: int, strategy: Strategy) -> CandidateRevision:
        system = self.schema_prompt("CandidateRevision")
        candidate_id = f"candidate-{index}"
        user = self.single_candidate_schema_user(text=text, candidate_id=candidate_id, strategy=strategy)
        data = self.complete_json_with_repair(system=system, user=user, schema_name="CandidateRevision")
        candidate = self.validate_payload(
            data=data,
            schema_name="CandidateRevision",
            system=system,
            user=user,
            validator=CandidateRevision.model_validate,
        )
        candidate.candidate_id = candidate_id
        candidate.strategy = strategy
        return candidate

    def complete_json_with_repair(self, *, system: str, user: str, schema_name: str):
        try:
            return self.llm.complete_json(system=system, user=user, schema_name=schema_name)
        except Exception as first_error:
            repair_system = (
                f"{system}\n\n"
                f"The previous {schema_name} response was invalid. Return only valid JSON for {schema_name}. "
                "Do not include Markdown fences or explanatory text. Preserve citations, numbers, facts, claims, "
                "terminology, and argument structure."
            )
            try:
                return self.llm.complete_json(system=repair_system, user=user, schema_name=schema_name)
            except Exception as second_error:
                raise ValueError(f"{schema_name} response failed validation after one repair attempt") from second_error

    def detector_results(self, text: str, providers: list[DetectorProvider] | None = None):
        providers = providers or self.detectors
        if self.config.detector_execution_mode == "parallel" and self.config.detector_concurrency > 1 and len(providers) > 1:
            with ThreadPoolExecutor(max_workers=self.config.detector_concurrency) as executor:
                return list(executor.map(lambda provider: provider.analyze(text), providers))
        return [provider.analyze(text) for provider in providers]

    def batch_detector_results(
        self,
        candidates: list[CandidateRevision],
        providers: list[DetectorProvider],
    ) -> dict[str, list]:
        results = {candidate.candidate_id: [] for candidate in candidates}
        batch_providers = [provider for provider in providers if hasattr(provider, "analyze_batch")]
        single_providers = [provider for provider in providers if provider not in batch_providers]
        for provider in batch_providers:
            batch = provider.analyze_batch([(candidate.candidate_id, candidate.rewritten_text) for candidate in candidates])
            for candidate_id, detector_results in batch.items():
                results.setdefault(candidate_id, []).extend(detector_results)
        for candidate in candidates:
            if single_providers:
                results[candidate.candidate_id].extend(self.detector_results(candidate.rewritten_text, single_providers))
        return results

    def split_detector_providers(self) -> tuple[list[DetectorProvider], list[DetectorProvider]]:
        teachers = [provider for provider in self.detectors if is_teacher_detector(provider)]
        baseline = [provider for provider in self.detectors if not is_teacher_detector(provider)]
        return baseline, teachers

    def should_stage_teacher_detectors(self, candidate_count: int) -> bool:
        return self.config.flash_mode == "production" and candidate_count > self.config.community_candidate_limit

    def ensure_final_community_signals(
        self,
        *,
        selected: CandidateRevision,
        score,
        detectors,
        original_text: str,
        semantic: SemanticRepresentation,
    ):
        _, teacher_providers = self.split_detector_providers()
        if not teacher_providers:
            return score, detectors
        existing = {detector.provider_name for detector in detectors}
        missing = [provider for provider in teacher_providers if provider.provider_name not in existing]
        if not missing:
            return score, detectors
        detectors = detectors + self.detector_results(selected.rewritten_text, missing)
        score = score_candidate(
            original_text=original_text,
            revised_text=selected.rewritten_text,
            semantic=semantic,
            detector_results=detectors,
            risk_flags=selected.risk_flags,
        )
        return score, detectors

    def detector_consensus_score(self, text: str) -> float:
        score = score_candidate(
            original_text=text,
            revised_text=text,
            semantic=SemanticRepresentation(),
            detector_results=self.detector_results(text),
            risk_flags=[],
        )
        return score.detector_risk_score

    def rank_candidates(self, original_text: str, candidates: list[CandidateRevision], semantic: SemanticRepresentation) -> list[RankedCandidate]:
        ranked: list[RankedCandidate] = []
        baseline_providers, teacher_providers = self.split_detector_providers()
        staged_teachers = bool(teacher_providers and baseline_providers and self.should_stage_teacher_detectors(len(candidates)))
        initial_providers = baseline_providers if staged_teachers else (baseline_providers + teacher_providers)
        batched_results = self.batch_detector_results(candidates, initial_providers)
        for candidate in candidates:
            detectors = batched_results.get(candidate.candidate_id, [])
            score = score_candidate(
                original_text=original_text,
                revised_text=candidate.rewritten_text,
                semantic=semantic,
                detector_results=detectors,
                risk_flags=candidate.risk_flags,
            )
            ranked.append(
                RankedCandidate(
                    candidate=candidate,
                    detector_results=detectors,
                    score_card=score,
                    rank=0,
                    passed_hard_constraints=not score.hard_constraint_failures,
                )
            )
        if staged_teachers:
            ranked.sort(key=lambda item: (item.passed_hard_constraints, item.score_card.candidate_utility), reverse=True)
            top_ids = {item.candidate.candidate_id for item in ranked[: self.config.community_candidate_limit]}
            top_items = [item for item in ranked if item.candidate.candidate_id in top_ids]
            teacher_batch = self.batch_detector_results([item.candidate for item in top_items], teacher_providers)
            for item in top_items:
                detectors = item.detector_results + teacher_batch.get(item.candidate.candidate_id, [])
                item.detector_results = detectors
                item.score_card = score_candidate(
                    original_text=original_text,
                    revised_text=item.candidate.rewritten_text,
                    semantic=semantic,
                    detector_results=detectors,
                    risk_flags=item.candidate.risk_flags,
                )
                item.passed_hard_constraints = not item.score_card.hard_constraint_failures
        ranked.sort(key=lambda item: (item.passed_hard_constraints, item.score_card.candidate_utility), reverse=True)
        for index, item in enumerate(ranked, start=1):
            item.rank = index
        return ranked

    def refine(self, original_text: str, ranked: list[RankedCandidate], semantic: SemanticRepresentation) -> list[RefinementCycle]:
        cycles: list[RefinementCycle] = []
        current_item = self.initial_refinement_target(ranked)
        current = current_item.candidate
        current_score = current_item.score_card
        current_detectors = current_item.detector_results
        rejection_feedback: list[str] = []
        for cycle_number in range(1, self.config.max_refinement_cycles + 1):
            if current_score.weighted_quality >= self.config.quality_threshold and current_score.detector_risk_score <= self.config.detector_risk_target:
                break
            diagnostics = build_refinement_diagnostics(
                original_text=original_text,
                current_text=current.rewritten_text,
                score_card=current_score,
                detector_results=current_detectors,
                semantic=semantic,
            )
            refinement_user = self.diagnostic_refinement_schema_user(
                current.rewritten_text,
                diagnostics,
                score_summary={
                    "candidate_utility": current_score.candidate_utility,
                    "weighted_quality": current_score.weighted_quality,
                    "detector_risk_score": current_score.detector_risk_score,
                    "hard_constraint_failures": current_score.hard_constraint_failures,
                },
                rejection_feedback=rejection_feedback,
            )
            data = self.complete_json_with_repair(
                system=self.schema_prompt("RefinedCandidate"),
                user=refinement_user,
                schema_name="RefinedCandidate",
            )
            refined = self.validate_payload(
                data=data,
                schema_name="RefinedCandidate",
                system=self.schema_prompt("RefinedCandidate"),
                user=refinement_user,
                validator=CandidateRevision.model_validate,
            )
            refined.candidate_id = f"{current.candidate_id}-r{cycle_number}"
            detectors = self.detector_results(refined.rewritten_text)
            score = score_candidate(
                original_text=original_text,
                revised_text=refined.rewritten_text,
                semantic=semantic,
                detector_results=detectors,
                risk_flags=refined.risk_flags,
            )
            non_disruptive_score = non_disruptive_change_score(original_text, refined.rewritten_text)
            utility_gain = score.candidate_utility - current_score.candidate_utility
            detector_risk_drop = current_score.detector_risk_score - score.detector_risk_score
            refined_diagnostics = build_refinement_diagnostics(
                original_text=original_text,
                current_text=refined.rewritten_text,
                score_card=score,
                detector_results=detectors,
                semantic=semantic,
            )
            diagnostic_gain = targeted_diagnostic_improvement(diagnostics, refined_diagnostics)
            accepted_for_next_cycle = (
                not score.hard_constraint_failures
                and (
                    utility_gain >= 0.005
                    or (detector_risk_drop >= 0.03 and non_disruptive_score >= 0.55)
                    or (
                        diagnostic_gain >= 0.08
                        and detector_risk_drop >= -0.01
                        and utility_gain >= -0.04
                        and non_disruptive_score >= 0.55
                    )
                )
            )
            notes = [
                "Detector risk, preservation, and quality were rescored after diagnostic refinement.",
                f"Diagnostic failure modes: {', '.join(diagnostics.failure_modes)}.",
                f"Targeted diagnostic gain: {diagnostic_gain:.4f}.",
            ]
            if accepted_for_next_cycle:
                notes.append("Diagnostic refinement accepted as the next cycle baseline.")
            else:
                notes.append("Diagnostic refinement rejected as next baseline; preservation or utility did not improve enough.")
            cycles.append(
                RefinementCycle(
                    cycle_number=cycle_number,
                    starting_candidate_id=current.candidate_id,
                    refined_candidate=refined,
                    detector_results=detectors,
                    score_card=score,
                    notes=notes,
                    diagnostic_context={
                        **diagnostics.model_dump(mode="json"),
                        "refined_failure_modes": refined_diagnostics.failure_modes,
                        "targeted_diagnostic_gain": diagnostic_gain,
                    },
                    accepted_for_next_cycle=accepted_for_next_cycle,
                )
            )
            if not accepted_for_next_cycle:
                if score.hard_constraint_failures:
                    break
                rejection_feedback = [
                    f"Previous attempt utility delta was {utility_gain:.4f}; required at least 0.005 unless detector risk dropped materially.",
                    f"Previous attempt detector risk delta was {detector_risk_drop:.4f}; required at least 0.03 with non-disruptive edits.",
                    f"Previous attempt targeted diagnostic gain was {diagnostic_gain:.4f}; required at least 0.08 without detector-risk or utility regression.",
                    f"Previous attempt non-disruptive score was {non_disruptive_score:.4f}; required at least 0.55 for detector-risk-only acceptance.",
                    "Do not repeat the same surface phrasing; address the failure modes with concrete local edits.",
                ]
                continue
            current = refined
            current_score = score
            current_detectors = detectors
            if score.hard_constraint_failures:
                break
            rejection_feedback = []
        return cycles

    def initial_refinement_target(self, ranked: list[RankedCandidate]) -> RankedCandidate:
        safe_ranked = [item for item in ranked if item.passed_hard_constraints]
        options = safe_ranked or ranked
        return max(
            options,
            key=lambda item: (
                round(item.score_card.candidate_utility, 2),
                -item.score_card.detector_risk_score,
                item.score_card.weighted_quality,
            ),
        )

    def schema_user(self, text: str) -> str:
        return f"TEXT:\n{text}\n\nReturn JSON only."

    def single_candidate_schema_user(self, *, text: str, candidate_id: str, strategy: Strategy) -> str:
        return (
            f"CANDIDATE_ID: {candidate_id}\n"
            f"STRATEGY: {strategy.value}\n"
            f"TEXT:\n{text}\n\n"
            "Return JSON only."
        )

    def diagnostic_refinement_schema_user(
        self,
        text: str,
        diagnostics,
        *,
        score_summary: dict[str, object] | None = None,
        rejection_feedback: list[str] | None = None,
    ) -> str:
        score_block = f"CURRENT_SCORE_SUMMARY:\n{score_summary}\n\n" if score_summary else ""
        rejection_block = ""
        if rejection_feedback:
            rejection_block = "PREVIOUS_REJECTION_FEEDBACK:\n" + "\n".join(f"- {item}" for item in rejection_feedback) + "\n\n"
        return (
            f"{render_refinement_prompt_context(diagnostics)}\n\n"
            f"{score_block}"
            f"{rejection_block}"
            "Rewrite with bounded, local changes that address the diagnostic plan. Preserve all hard constraints.\n"
            "The revision should be measurably better than the current candidate: improve specificity, rhythm, or naturalness "
            "while keeping citations, numbers, terminology, and factual claims intact. Avoid merely adding a generic prefix, "
            "changing wording cosmetically, or making broad paraphrases.\n\n"
            f"TEXT:\n{text}\n\n"
            "Return JSON only."
        )

    def schema_prompt(self, schema_name: str) -> str:
        if schema_name == "SemanticRepresentation":
            return (
                "Analyze the provided academic TEXT and return only one JSON object. "
                "Required keys: claims, entities, relations, disciplinary_terms, citations_or_references, "
                "exact_citation_spans, numeric_values, argument_structure, uncertainty_markers, "
                "non_negotiable_preservation_items. Every value must be a list of strings. "
                "Copy citation spans and numeric values exactly as they appear. Do not invent references."
            )
        if schema_name == "AcademicProfile":
            return (
                "Classify the provided academic TEXT, not any cited author or named person. "
                "Return only one JSON object with keys: discipline, subdiscipline, document_type, audience, "
                "writing_level, author_needs, style_constraints, inferred_fields. "
                "discipline and document_type are required strings. Use document_type='essay' unless the text "
                "clearly indicates another academic form. author_needs, style_constraints, and inferred_fields "
                "must be lists of strings."
            )
        if schema_name == "CandidateRevisions":
            return (
                "Rewrite the academic TEXT into candidate revisions. Return only JSON in this exact shape: "
                "{\"candidates\":[{\"candidate_id\":\"candidate-1\",\"rewritten_text\":\"...\","
                "\"strategy\":\"conservative_academic\",\"intended_improvements\":[\"...\"],"
                "\"preservation_notes\":[\"...\"],\"risk_flags\":[]}]}. "
                "Return 5 to 7 candidates with at least 5 distinct strategies chosen from: "
                "conservative_academic, natural_scholarly, enhanced_clarity, structural_optimization, "
                "stylistic_maturation, non_native_refinement, precision_oriented. Preserve all citations, "
                "numbers, facts, claims, terminology, and argument structure. Do not add references."
            )
        if schema_name == "CandidateRevision":
            return (
                "Rewrite the academic TEXT into exactly one candidate revision for the requested STRATEGY and "
                "CANDIDATE_ID. Return only one JSON object with keys: candidate_id, rewritten_text, strategy, "
                "intended_improvements, preservation_notes, risk_flags. Use the requested strategy exactly. "
                "Preserve every citation span, numeric value, factual claim, disciplinary term, and the argument "
                "structure. Do not add references, remove citations, or invent evidence."
            )
        if schema_name == "RefinedCandidate":
            return (
                "Improve the selected academic candidate without semantic disruption. Return only one JSON object "
                "with keys: candidate_id, rewritten_text, strategy, intended_improvements, preservation_notes, "
                "risk_flags. strategy must be one of: conservative_academic, natural_scholarly, enhanced_clarity, "
                "structural_optimization, stylistic_maturation, non_native_refinement, precision_oriented. "
                "Preserve all citations, numbers, facts, claims, terminology, and argument structure exactly. "
                "Do not add references."
            )
        raise ValueError(f"Unsupported schema prompt: {schema_name}")

    def parse_candidate_revisions(self, data) -> list[CandidateRevision]:
        data = self.unwrap_schema_payload(data, "CandidateRevisions")
        candidates = [CandidateRevision.model_validate(item) for item in data["candidates"]]
        if len({candidate.strategy for candidate in candidates}) < 5:
            raise ValueError("candidate generation must include at least five strategies")
        return candidates

    def validate_payload(self, *, data, schema_name: str, system: str, user: str, validator):
        unwrapped = self.unwrap_schema_payload(data, schema_name)
        unwrapped = self.coerce_schema_payload(unwrapped, schema_name)
        try:
            return validator(unwrapped)
        except Exception as first_error:
            repair_system = (
                f"{system}\n\n"
                f"The previous JSON did not match {schema_name}: {first_error}. "
                "Return corrected JSON only. Keep the requested top-level shape. "
                "Do not include Markdown fences or commentary."
            )
            repaired = self.complete_json_with_repair(system=repair_system, user=user, schema_name=schema_name)
            repaired = self.unwrap_schema_payload(repaired, schema_name)
            repaired = self.coerce_schema_payload(repaired, schema_name)
            try:
                return validator(repaired)
            except Exception as second_error:
                raise ValueError(f"{schema_name} response failed schema validation after repair") from second_error

    def coerce_schema_payload(self, payload, schema_name: str):
        if schema_name not in {"CandidateRevision", "RefinedCandidate"} or not isinstance(payload, dict):
            return payload
        coerced = dict(payload)
        for key in ("intended_improvements", "preservation_notes", "risk_flags"):
            value = coerced.get(key)
            if value is None:
                coerced[key] = []
            elif isinstance(value, str):
                coerced[key] = [value]
        return coerced

    def unwrap_schema_payload(self, data, schema_name: str):
        if not isinstance(data, dict):
            return data
        if schema_name == "CandidateRevisions" and "candidates" in data:
            return data
        wrapper_keys = {
            "SemanticRepresentation": ("semantic_representation", "semantic", "representation", "data", "result"),
            "AcademicProfile": ("academic_profile", "profile", "data", "result"),
            "CandidateRevisions": ("candidate_revisions", "revisions", "data", "result"),
            "CandidateRevision": ("candidate_revision", "candidate", "revision", "data", "result"),
            "RefinedCandidate": ("refined_candidate", "candidate", "revision", "data", "result"),
        }[schema_name]
        for key in wrapper_keys:
            value = data.get(key)
            if isinstance(value, dict):
                return self.unwrap_schema_payload(value, schema_name)
        if len(data) == 1:
            value = next(iter(data.values()))
            if isinstance(value, dict):
                return self.unwrap_schema_payload(value, schema_name)
        return data

    def select_final_candidate(
        self,
        ranked: list[RankedCandidate],
        cycles: list[RefinementCycle],
        original_text: str,
        semantic: SemanticRepresentation,
    ):
        safe_options = [
            (ranked_candidate.candidate, ranked_candidate.score_card, ranked_candidate.detector_results)
            for ranked_candidate in ranked
            if ranked_candidate.passed_hard_constraints
        ]
        safe_options.extend(
            (cycle.refined_candidate, cycle.score_card, cycle.detector_results)
            for cycle in cycles
            if cycle.accepted_for_next_cycle and not cycle.score_card.hard_constraint_failures
        )
        if safe_options:
            return max(
                safe_options,
                key=lambda option: (
                    round(option[1].candidate_utility, 2),
                    -option[1].detector_risk_score,
                    option[1].weighted_quality,
                ),
            )
        return self.preservation_fallback(original_text, semantic)

    def preservation_fallback(self, original_text: str, semantic: SemanticRepresentation):
        fallback = CandidateRevision(
            candidate_id="preservation-fallback-original",
            rewritten_text=original_text,
            strategy=Strategy.conservative_academic,
            intended_improvements=[],
            preservation_notes=[
                "No generated candidate passed hard preservation gates; original text was returned unchanged."
            ],
            risk_flags=["no_safe_generated_candidate"],
        )
        detectors = self.detector_results(original_text)
        score = score_candidate(
            original_text=original_text,
            revised_text=original_text,
            semantic=semantic,
            detector_results=detectors,
            risk_flags=[],
        )
        score.false_positive_risk_notes.append(
            "No generated candidate passed hard preservation gates; detector score is reported on the original text."
        )
        return fallback, score, detectors

    def refinement_stop_reason(self, ranked: list[RankedCandidate], cycles: list[RefinementCycle], selected: CandidateRevision) -> str:
        if selected.candidate_id == "preservation-fallback-original":
            return "blocked_no_safe_candidate_preserved_original"
        if not cycles:
            score = ranked[0].score_card
            if score.weighted_quality >= self.config.quality_threshold and score.detector_risk_score <= self.config.detector_risk_target:
                return "initial_candidate_met_quality_and_detector_targets"
            return "no_refinement_cycles_configured"
        last_score = cycles[-1].score_card
        if last_score.hard_constraint_failures:
            return "stopped_after_hard_constraint_failure"
        if not cycles[-1].accepted_for_next_cycle:
            return "refinement_rejected_no_safe_improvement"
        if last_score.weighted_quality >= self.config.quality_threshold and last_score.detector_risk_score <= self.config.detector_risk_target:
            return "refined_candidate_met_quality_and_detector_targets"
        if len(cycles) >= self.config.max_refinement_cycles:
            return "max_refinement_cycles_reached"
        return "refinement_stopped"

    def final_selection_summary(
        self,
        selected: CandidateRevision,
        score,
        ranked: list[RankedCandidate],
        cycles: list[RefinementCycle],
    ) -> dict[str, object]:
        source = "ranked_candidate"
        rank = next((item.rank for item in ranked if item.candidate.candidate_id == selected.candidate_id), None)
        cycle_number = None
        if selected.candidate_id == "preservation-fallback-original":
            source = "preservation_fallback"
        for cycle in cycles:
            if cycle.refined_candidate.candidate_id == selected.candidate_id:
                source = "refinement_cycle"
                cycle_number = cycle.cycle_number
                rank = None
                break
        return {
            "candidate_id": selected.candidate_id,
            "strategy": selected.strategy.value,
            "source": source,
            "rank": rank,
            "cycle_number": cycle_number,
            "utility": score.candidate_utility,
            "weighted_quality": score.weighted_quality,
            "detector_risk_score": score.detector_risk_score,
            "detector_label_consensus": score.detector_label_consensus,
            "detector_disagreement": score.detector_disagreement,
            "hard_constraint_failures": score.hard_constraint_failures,
        }

    def refinement_loop_summary(self, ranked: list[RankedCandidate], cycles: list[RefinementCycle]) -> list[dict[str, object]]:
        initial_item = ranked[0]
        if cycles:
            initial_item = next(
                (item for item in ranked if item.candidate.candidate_id == cycles[0].starting_candidate_id),
                ranked[0],
            )
        rows: list[dict[str, object]] = [
            {
                "cycle_number": 0,
                "candidate_id": initial_item.candidate.candidate_id,
                "score": initial_item.score_card.candidate_utility,
                "weighted_quality": initial_item.score_card.weighted_quality,
                "detector_risk_score": initial_item.score_card.detector_risk_score,
                "detector_label_consensus": initial_item.score_card.detector_label_consensus,
                "constraint_failures": initial_item.score_card.hard_constraint_failures,
                "notes": ["Initial diagnostic refinement target before refinement."],
            }
        ]
        rows.extend(
            {
                "cycle_number": cycle.cycle_number,
                "candidate_id": cycle.refined_candidate.candidate_id,
                "score": cycle.score_card.candidate_utility,
                "weighted_quality": cycle.score_card.weighted_quality,
                "detector_risk_score": cycle.score_card.detector_risk_score,
                "detector_label_consensus": cycle.score_card.detector_label_consensus,
                "constraint_failures": cycle.score_card.hard_constraint_failures,
                "accepted_for_next_cycle": cycle.accepted_for_next_cycle,
                "diagnostic_failure_modes": cycle.diagnostic_context.get("failure_modes", []),
                "notes": cycle.notes,
            }
            for cycle in cycles
        )
        return rows

    def non_disruptive_summary(self, original_text: str, selected: CandidateRevision, score) -> dict[str, object]:
        return {
            "score": non_disruptive_change_score(original_text, selected.rewritten_text),
            "semantic_fidelity": score.semantic_fidelity,
            "factual_consistency": score.factual_consistency,
            "changed_word_count_delta": len(selected.rewritten_text.split()) - len(original_text.split()),
            "preservation_gate": "passed" if not score.hard_constraint_failures else "failed",
            "summary": (
                "Selected candidate preserves hard constraints while making bounded academic style changes."
                if not score.hard_constraint_failures
                else "Selected fallback has preservation warnings; review hard constraint failures before use."
            ),
        }

    def final_report(
        self,
        selected: CandidateRevision,
        score,
        detectors,
        ranked: list[RankedCandidate],
        cycles: list[RefinementCycle],
        normalized: NormalizedInput,
        semantic: SemanticRepresentation,
        profile: AcademicProfile,
    ) -> RevisionReport:
        warnings = list(normalized.warnings) + score.hard_constraint_failures
        if selected.candidate_id == "preservation-fallback-original":
            warnings.append("No generated candidate passed hard preservation gates; original text returned unchanged.")
        if score.detector_risk_score > self.config.detector_risk_target:
            warnings.append("Detector-risk target was not fully reached without risking preservation constraints.")
        return RevisionReport(
            refined_text=selected.rewritten_text,
            major_revisions=selected.intended_improvements,
            semantic_preservation_analysis={
                "citations_preserved": all(citation in selected.rewritten_text for citation in semantic.exact_citation_spans),
                "numeric_values_preserved": all(value in selected.rewritten_text for value in semantic.numeric_values),
                "hard_constraint_failures": score.hard_constraint_failures,
                "policy": "Citations, facts, claims, terminology, and argument structure are hard gates.",
            },
            academic_quality_analysis={
                "discipline": profile.discipline,
                "weighted_quality": score.weighted_quality,
                "candidate_utility": score.candidate_utility,
                "top_ranked_strategy": ranked[0].candidate.strategy.value,
                "selected_candidate": self.final_selection_summary(selected, score, ranked, cycles),
                "stop_reason": self.refinement_stop_reason(ranked, cycles, selected),
                "refinement_loop": self.refinement_loop_summary(ranked, cycles),
                "non_disruptive_change_summary": self.non_disruptive_summary(normalized.original_text, selected, score),
                "diagnostic_refinement": [
                    {
                        "cycle_number": cycle.cycle_number,
                        "starting_candidate_id": cycle.starting_candidate_id,
                        "candidate_id": cycle.refined_candidate.candidate_id,
                        "accepted_for_next_cycle": cycle.accepted_for_next_cycle,
                        "failure_modes": cycle.diagnostic_context.get("failure_modes", []),
                        "rewrite_recommendations": cycle.diagnostic_context.get("rewrite_recommendations", []),
                        "detector_interpretation": cycle.diagnostic_context.get("detector_interpretation", {}),
                        "change_budget": cycle.diagnostic_context.get("change_budget", {}),
                    }
                    for cycle in cycles
                ],
            },
            style_analysis=score.naturalness_diagnostics,
            detector_signal_analysis={
                "detector_risk_score": score.detector_risk_score,
                "label_consensus": score.detector_label_consensus,
                "disagreement": score.detector_disagreement,
                "notes": score.false_positive_risk_notes,
                "execution_mode": self.config.detector_execution_mode,
                "community_detectors": [detector.provider_name for detector in detectors if detector.provider_name.startswith("community_")],
                "available_community_detectors": [
                    detector.provider_name for detector in detectors if detector.provider_name.startswith("community_") and detector.available
                ],
                "flash_mode": self.config.flash_mode,
                "flash_detectors": [detector.provider_name for detector in detectors if detector.provider_name.startswith("flash_")],
                "available_flash_detectors": [
                    detector.provider_name for detector in detectors if detector.provider_name.startswith("flash_") and detector.available
                ],
                "unavailable_detectors": [
                    {"provider_name": detector.provider_name, "error": detector.error}
                    for detector in detectors
                    if not detector.available
                ],
                "detectors": [detector.model_dump(mode="json") for detector in detectors],
                "caveat": "Detector-risk signals are heuristics and do not guarantee any detection outcome.",
            },
            warnings=warnings,
            optional_detector_audit=detectors,
            excluded_candidate_audit=build_excluded_candidate_audit(
                ranked=ranked,
                cycles=cycles,
                selected_id=selected.candidate_id,
            ),
        )

    def calibration_audit(self, input_path: Path, output_path: Path) -> dict[str, object]:
        result = self.run_text(input_path.read_text(encoding="utf-8"), input_path=str(input_path), write_artifact=False)
        selected_id = result.final_report.academic_quality_analysis["selected_candidate"]["candidate_id"]
        excluded_by_id = {
            audit.candidate_id: audit
            for audit in build_excluded_candidate_audit(
                ranked=result.ranked_candidates,
                cycles=result.refinement_cycles,
                selected_id=selected_id,
            )
        }
        candidate_audits: list[dict[str, object]] = []
        for item in result.ranked_candidates:
            excluded = excluded_by_id.get(item.candidate.candidate_id)
            candidate_audits.append(
                {
                    "candidate_id": item.candidate.candidate_id,
                    "source": "ranked_candidate",
                    "rank": item.rank,
                    "cycle_number": None,
                    "strategy": item.candidate.strategy.value,
                    "prompt_metadata": {
                        "generator_model": self.config.deepseek_model if not self.config.use_mock_provider else "deterministic_mock",
                        "detector_set": self.config.detector_set,
                        "flash_mode": self.config.flash_mode,
                    },
                    "detector_scores": [detector.model_dump(mode="json") for detector in item.detector_results],
                    "preservation_quality": item.score_card.model_dump(mode="json"),
                    "winner": item.candidate.candidate_id == selected_id,
                    "failure_notes": item.score_card.hard_constraint_failures,
                    "exclusion_reasons": excluded.exclusion_reasons if excluded else [],
                    "failure_modes": [mode.value for mode in excluded.failure_modes] if excluded else [],
                }
            )
        for cycle in result.refinement_cycles:
            excluded = excluded_by_id.get(cycle.refined_candidate.candidate_id)
            candidate_audits.append(
                {
                    "candidate_id": cycle.refined_candidate.candidate_id,
                    "source": "refinement_cycle",
                    "rank": None,
                    "cycle_number": cycle.cycle_number,
                    "strategy": cycle.refined_candidate.strategy.value,
                    "prompt_metadata": {
                        "generator_model": self.config.deepseek_model if not self.config.use_mock_provider else "deterministic_mock",
                        "detector_set": self.config.detector_set,
                        "flash_mode": self.config.flash_mode,
                        "starting_candidate_id": cycle.starting_candidate_id,
                    },
                    "detector_scores": [detector.model_dump(mode="json") for detector in cycle.detector_results],
                    "preservation_quality": cycle.score_card.model_dump(mode="json"),
                    "winner": cycle.refined_candidate.candidate_id == selected_id,
                    "failure_notes": cycle.score_card.hard_constraint_failures + cycle.notes,
                    "exclusion_reasons": excluded.exclusion_reasons if excluded else [],
                    "failure_modes": [mode.value for mode in excluded.failure_modes] if excluded else [],
                    "diagnostic_context": cycle.diagnostic_context,
                    "accepted_for_next_cycle": cycle.accepted_for_next_cycle,
                }
            )
        artifact = {
            "artifact_type": "academic_engine_calibration_audit",
            "input_path": str(input_path),
            "run_id": result.run_id,
            "detector_set": self.config.detector_set,
            "flash_mode": self.config.flash_mode,
            "teacher_detector_policy": "all_candidates" if self.config.flash_mode in {"calibration", "research"} else "production_top_k_then_final",
            "selected_candidate": result.final_report.academic_quality_analysis["selected_candidate"],
            "candidate_audits": candidate_audits,
            "final_detector_signal_analysis": result.final_report.detector_signal_analysis,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
        return artifact

    def raw_detector_audit(self, input_paths: list[Path], output_path: Path) -> dict[str, object]:
        samples: dict[str, object] = {}
        for input_path in input_paths:
            text = input_path.read_text(encoding="utf-8")
            detectors = self.detector_results(text)
            risk, consensus, disagreement, notes = detector_consensus(detectors)
            samples[input_path.stem] = {
                "input_path": str(input_path),
                "word_count": len(text.split()),
                "detector_risk_score": risk,
                "label_consensus": consensus,
                "detector_disagreement": disagreement,
                "notes": notes,
                "detectors": [detector.model_dump(mode="json") for detector in detectors],
            }
        artifact = {
            "artifact_type": "academic_engine_raw_detector_audit",
            "detector_set": self.config.detector_set,
            "flash_mode": self.config.flash_mode,
            "samples": samples,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
        return artifact

    def run_file(self, input_path: Path) -> PipelineResult:
        return self.run_text(input_path.read_text(encoding="utf-8"), input_path=str(input_path))

    def experiment(self, fixture_dir: Path) -> ExperimentSummary:
        results: list[ExperimentFixtureResult] = []
        for fixture in sorted(fixture_dir.glob("*.txt")):
            text = fixture.read_text(encoding="utf-8")
            before = self.detector_consensus_score(text)
            result = self.run_text(text, input_path=str(fixture), write_artifact=True)
            selected_summary = result.final_report.academic_quality_analysis["selected_candidate"]
            after = result.final_report.detector_signal_analysis["detector_risk_score"]
            results.append(
                ExperimentFixtureResult(
                    fixture_path=str(fixture),
                    before_detector_risk=before,
                    after_detector_risk=after,
                    final_quality=selected_summary["weighted_quality"],
                    utility=selected_summary["utility"],
                    non_disruptive_change_score=non_disruptive_change_score(text, result.final_report.refined_text),
                    preservation_warnings=result.final_report.warnings,
                    hard_constraint_failures=selected_summary["hard_constraint_failures"],
                    artifact_path=result.artifact_path,
                )
            )
        if not results:
            raise ValueError(f"no .txt fixtures found in {fixture_dir}")
        summary = ExperimentSummary(
            fixture_dir=str(fixture_dir),
            fixture_count=len(results),
            average_before_detector_risk=round(sum(item.before_detector_risk for item in results) / len(results), 4),
            average_after_detector_risk=round(sum(item.after_detector_risk for item in results) / len(results), 4),
            average_final_quality=round(sum(item.final_quality for item in results) / len(results), 4),
            average_non_disruptive_change_score=round(sum(item.non_disruptive_change_score for item in results) / len(results), 4),
            results=results,
        )
        artifact = self.config.runs_dir / f"{uuid.uuid4().hex[:12]}--experiment-summary.json"
        summary.artifact_path = str(artifact)
        artifact.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return summary
