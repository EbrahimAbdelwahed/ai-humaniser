from __future__ import annotations

from academic_engine.schemas import ExcludedCandidateAudit, FailureMode, RankedCandidate, RefinementCycle


def failure_modes_from_candidate(item: RankedCandidate) -> list[FailureMode]:
    score = item.score_card
    modes: set[FailureMode] = set()
    for failure in score.hard_constraint_failures:
        lowered = failure.lower()
        modes.add(FailureMode.hard_gate_failure)
        if "citation" in lowered:
            modes.add(FailureMode.citation_drift)
        if "numeric" in lowered:
            modes.add(FailureMode.numeric_drift)
        if "disciplinary term" in lowered or "terminology" in lowered:
            modes.add(FailureMode.terminology_drift)
    if score.semantic_fidelity < 0.70:
        modes.add(FailureMode.semantic_drift)
    if score.detector_risk_score >= 0.62:
        modes.add(FailureMode.high_artificiality_risk)
    if score.academic_authenticity < 0.62 or score.naturalness_diagnostics.get("repetitive_structure_risk", 0.0) > 0.12:
        modes.add(FailureMode.low_naturalness)
    if score.stylistic_sophistication < 0.58:
        modes.add(FailureMode.low_specificity)
    for detector in item.detector_results:
        if detector.available:
            continue
        modes.add(FailureMode.detector_unavailable)
        error = (detector.error or "").lower()
        provider = detector.provider_name.lower()
        if "runpod" in error or provider.startswith("flash_"):
            modes.add(FailureMode.runpod_unavailable)
        if "parse" in error or "unsupported output" in error or "did not include" in error:
            modes.add(FailureMode.malformed_detector_response)
        if "timeout" in error or "timed out" in error:
            modes.add(FailureMode.timeout)
    return sorted(modes, key=lambda mode: mode.value)


def exclusion_reasons(item: RankedCandidate, selected_id: str) -> list[str]:
    reasons: list[str] = []
    if item.candidate.candidate_id == selected_id:
        return reasons
    if item.score_card.hard_constraint_failures:
        reasons.append("failed hard preservation gate")
    if item.score_card.detector_risk_score >= 0.62:
        reasons.append("high artificiality risk")
    if item.score_card.academic_authenticity < 0.62:
        reasons.append("low naturalness")
    if item.rank and item.rank > 1:
        reasons.append(f"ranked below selected candidate at rank {item.rank}")
    return reasons or ["not selected by composite academic quality and preservation reward"]


def build_excluded_candidate_audit(
    *,
    ranked: list[RankedCandidate],
    cycles: list[RefinementCycle],
    selected_id: str,
) -> list[ExcludedCandidateAudit]:
    audits: list[ExcludedCandidateAudit] = []
    for item in ranked:
        if item.candidate.candidate_id == selected_id:
            continue
        audits.append(
            ExcludedCandidateAudit(
                candidate_id=item.candidate.candidate_id,
                strategy=item.candidate.strategy.value,
                text=item.candidate.rewritten_text,
                scores={
                    "rank": item.rank,
                    "candidate_utility": item.score_card.candidate_utility,
                    "weighted_quality": item.score_card.weighted_quality,
                    "detector_risk_score": item.score_card.detector_risk_score,
                    "semantic_fidelity": item.score_card.semantic_fidelity,
                    "factual_consistency": item.score_card.factual_consistency,
                },
                hard_constraint_failures=item.score_card.hard_constraint_failures,
                exclusion_reasons=exclusion_reasons(item, selected_id),
                failure_modes=failure_modes_from_candidate(item),
            )
        )
    for cycle in cycles:
        if cycle.refined_candidate.candidate_id == selected_id:
            continue
        synthetic = RankedCandidate(
            candidate=cycle.refined_candidate,
            detector_results=cycle.detector_results,
            score_card=cycle.score_card,
            rank=0,
            passed_hard_constraints=not cycle.score_card.hard_constraint_failures,
        )
        audits.append(
            ExcludedCandidateAudit(
                candidate_id=cycle.refined_candidate.candidate_id,
                strategy=cycle.refined_candidate.strategy.value,
                text=cycle.refined_candidate.rewritten_text,
                scores={
                    "cycle_number": cycle.cycle_number,
                    "candidate_utility": cycle.score_card.candidate_utility,
                    "weighted_quality": cycle.score_card.weighted_quality,
                    "detector_risk_score": cycle.score_card.detector_risk_score,
                    "semantic_fidelity": cycle.score_card.semantic_fidelity,
                    "factual_consistency": cycle.score_card.factual_consistency,
                },
                hard_constraint_failures=cycle.score_card.hard_constraint_failures,
                exclusion_reasons=exclusion_reasons(synthetic, selected_id) + cycle.notes,
                failure_modes=failure_modes_from_candidate(synthetic),
            )
        )
    return audits
