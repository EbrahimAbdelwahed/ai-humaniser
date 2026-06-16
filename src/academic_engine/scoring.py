from __future__ import annotations

from collections import Counter

from academic_engine.schemas import DetectorResult, ScoreCard, SemanticRepresentation
from academic_engine.utils import clamp, similarity, word_tokens


DETECTOR_WEIGHTS = {
    "local_stylometry_burstiness": 0.20,
    "local_lexical_diversity": 0.17,
    "local_gltr_lite_probability_shape": 0.18,
    "local_repetition_genericity": 0.20,
    "local_readability_academic_pattern": 0.17,
    "local_heuristic_detector_risk": 0.08,
    "hf_roberta_base_openai_detector": 0.35,
    "community_binoculars": 0.70,
    "community_ghostbuster": 0.62,
    "community_mage": 0.62,
    "community_radar": 0.62,
    "official_binoculars": 0.90,
    "official_ghostbuster": 0.82,
    "official_fast_detectgpt": 0.82,
    "flash_binoculars": 0.90,
    "flash_ghostbuster": 0.82,
    "flash_mage": 0.82,
    "flash_roberta_cluster": 0.35,
    "flash_radar": 0.24,
    "flash_openai_roberta": 0.24,
    "flash_chatgpt_roberta": 0.24,
}


def detector_consensus(detector_results: list[DetectorResult]) -> tuple[float, str, float, list[str]]:
    available = [result for result in detector_results if result.available]
    if not available:
        return 0.0, "unavailable", 0.0, ["No detector signals were available for this candidate."]

    weighted_pairs: list[tuple[DetectorResult, float]] = []
    for result in available:
        base_weight = DETECTOR_WEIGHTS.get(result.provider_name, 0.10)
        weighted_pairs.append((result, base_weight * max(0.25, result.confidence)))
    weight_total = sum(weight for _, weight in weighted_pairs) or 1.0
    detector_risk = sum(result.score * weight for result, weight in weighted_pairs) / weight_total
    detector_disagreement = (max(result.score for result in available) - min(result.score for result in available)) if len(available) > 1 else 0.0

    label_weights: dict[str, float] = {}
    for result, weight in weighted_pairs:
        label_weights[result.label] = label_weights.get(result.label, 0.0) + weight
    consensus = max(label_weights.items(), key=lambda item: item[1])[0]

    notes: list[str] = []
    unavailable = [result.provider_name for result in detector_results if not result.available]
    if unavailable:
        notes.append(f"Unavailable optional detector signals: {', '.join(unavailable)}.")
    community_available = [result.provider_name for result in available if result.provider_kind.value == "local_model" and result.provider_name.startswith("community_")]
    if community_available:
        notes.append(f"Community detector signals weighted strongly: {', '.join(community_available)}.")
    official_available = [result.provider_name for result in available if result.provider_name.startswith("official_")]
    if official_available:
        notes.append(f"Official detector signals weighted strongly: {', '.join(official_available)}.")
    flash_available = [result.provider_name for result in available if result.provider_name.startswith("flash_")]
    if flash_available:
        notes.append(f"Flash teacher detector signals included: {', '.join(flash_available)}.")
    if "flash_roberta_cluster" in flash_available:
        notes.append("RADAR, OpenAI RoBERTa, and ChatGPT RoBERTa are consumed as one correlated roberta_cluster signal.")
    if detector_disagreement >= 0.35:
        notes.append("Detector signals disagree materially; treat the aggregate as a diagnostic summary, not a verdict.")
    return round(clamp(detector_risk), 4), consensus, round(clamp(detector_disagreement), 4), notes


def hard_constraint_failures(original_text: str, revised_text: str, semantic: SemanticRepresentation) -> list[str]:
    failures: list[str] = []
    for citation in semantic.exact_citation_spans:
        if citation not in revised_text:
            failures.append(f"missing citation span: {citation}")
    for value in semantic.numeric_values:
        if value not in revised_text:
            failures.append(f"missing numeric value: {value}")
    for term in semantic.disciplinary_terms:
        if term.lower() in original_text.lower() and term.lower() not in revised_text.lower():
            failures.append(f"missing disciplinary term: {term}")
    return failures


def non_disruptive_change_score(original_text: str, revised_text: str) -> float:
    ratio = similarity(original_text, revised_text)
    if ratio < 0.35:
        return 0.25
    return clamp(1.0 - abs(0.72 - ratio))


def naturalness_diagnostics(text: str) -> dict[str, float]:
    words = [word.lower() for word in word_tokens(text)]
    unique = len(set(words)) / max(1, len(words))
    counts = Counter(words)
    repeated = sum(1 for _, count in counts.items() if count >= 4) / max(1, len(counts))
    return {
        "syntactic_variation": clamp(0.55 + unique * 0.35),
        "lexical_diversity": round(clamp(unique), 4),
        "discourse_flexibility": clamp(0.72 - repeated),
        "repetitive_structure_risk": clamp(repeated),
        "generic_llm_pattern_risk": clamp(1.0 - unique),
    }


def score_candidate(
    *,
    original_text: str,
    revised_text: str,
    semantic: SemanticRepresentation,
    detector_results: list[DetectorResult],
    risk_flags: list[str],
) -> ScoreCard:
    failures = hard_constraint_failures(original_text, revised_text, semantic)
    detector_risk, consensus, detector_disagreement, detector_notes = detector_consensus(detector_results)
    diagnostics = naturalness_diagnostics(revised_text)
    citation_penalty = 0.18 if any("citation" in failure for failure in failures) else 0.0
    risk_penalty = min(0.20, 0.05 * len(risk_flags))
    sim = similarity(original_text, revised_text)
    semantic_fidelity = clamp(0.78 + 0.20 * sim - citation_penalty - risk_penalty - 0.12 * len(failures))
    factual_consistency = clamp(0.88 - citation_penalty - risk_penalty - 0.12 * len(failures))
    words = word_tokens(revised_text)
    avg_word_len = sum(len(word) for word in words) / max(1, len(words))
    academic_authenticity = clamp(0.66 + min(0.16, avg_word_len / 60.0) - 0.10 * diagnostics["generic_llm_pattern_risk"])
    logical_flow = clamp(0.68 + min(0.15, revised_text.count(";") * 0.02 + revised_text.count(".") * 0.004))
    tone = clamp(0.72 - 0.10 * revised_text.lower().count("very ") / max(1, len(words)))
    clarity = clamp(0.76 - max(0.0, (len(words) / max(1, revised_text.count(".") + 1) - 28) / 100.0))
    sophistication = clamp(0.62 + min(0.20, diagnostics["lexical_diversity"] * 0.24))
    notes = list(detector_notes)
    if detector_risk >= 0.62:
        notes.append("Detector ensemble sees elevated false-positive-prone pattern risk.")
    if diagnostics["repetitive_structure_risk"] > 0.08:
        notes.append("Repeated lexical patterns may reduce naturalness.")
    return ScoreCard.compute(
        semantic_fidelity=round(semantic_fidelity, 4),
        factual_consistency=round(factual_consistency, 4),
        academic_authenticity=round(academic_authenticity, 4),
        logical_flow_cohesion=round(logical_flow, 4),
        academic_tone_quality=round(tone, 4),
        clarity_readability=round(clarity, 4),
        stylistic_sophistication=round(sophistication, 4),
        detector_risk_score=round(detector_risk, 4),
        detector_label_consensus=consensus,
        detector_disagreement=round(detector_disagreement, 4),
        false_positive_risk_notes=notes,
        hard_constraint_failures=failures,
        naturalness_diagnostics=diagnostics,
        non_disruptive_edit_score=non_disruptive_change_score(original_text, revised_text),
    )
