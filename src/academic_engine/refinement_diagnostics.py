from __future__ import annotations

from collections import Counter
from statistics import pstdev
from typing import Any

from pydantic import BaseModel, Field

from academic_engine.schemas import DetectorResult, ScoreCard, SemanticRepresentation
from academic_engine.utils import clamp, extract_citations, extract_numbers, sentence_split, word_tokens


FORMULAIC_TRANSITIONS = (
    "it is important to note",
    "in conclusion",
    "furthermore",
    "moreover",
    "in this context",
    "this highlights",
    "this underscores",
    "it can be argued",
    "it should be noted",
)


class RefinementDiagnostics(BaseModel):
    failure_modes: list[str] = Field(default_factory=list)
    detector_interpretation: dict[str, Any] = Field(default_factory=dict)
    rewrite_recommendations: list[str] = Field(default_factory=list)
    preservation_constraints: list[str] = Field(default_factory=list)
    change_budget: dict[str, Any] = Field(default_factory=dict)
    stylometry: dict[str, float] = Field(default_factory=dict)


def _sentence_length_stats(text: str) -> tuple[float, float]:
    lengths = [len(word_tokens(sentence)) for sentence in sentence_split(text)]
    if not lengths:
        return 0.0, 0.0
    mean = sum(lengths) / len(lengths)
    deviation = pstdev(lengths) if len(lengths) > 1 else 0.0
    return round(mean, 4), round(deviation, 4)


def _stylometry(text: str) -> dict[str, float]:
    words = [word.lower() for word in word_tokens(text)]
    counts = Counter(words)
    unique_ratio = len(counts) / max(1, len(words))
    repeated_ratio = sum(1 for count in counts.values() if count >= 4) / max(1, len(counts))
    sentence_mean, sentence_stdev = _sentence_length_stats(text)
    formulaic_hits = sum(1 for marker in FORMULAIC_TRANSITIONS if marker in text.lower())
    specificity_markers = len(extract_numbers(text)) + len(extract_citations(text))
    specificity_density = specificity_markers / max(1, len(words) / 100)
    rhythm_variance = clamp(sentence_stdev / max(1.0, sentence_mean))
    return {
        "lexical_diversity": round(clamp(unique_ratio), 4),
        "repetition_risk": round(clamp(repeated_ratio * 3.0), 4),
        "sentence_length_mean": round(sentence_mean, 4),
        "sentence_length_stdev": round(sentence_stdev, 4),
        "uniform_rhythm_risk": round(clamp(1.0 - rhythm_variance * 3.0), 4),
        "formulaic_transition_density": round(clamp(formulaic_hits / max(1, len(sentence_split(text))) * 2.0), 4),
        "specificity_density": round(clamp(specificity_density), 4),
        "low_specificity_risk": round(clamp(1.0 - specificity_density), 4),
    }


def _score_by_provider(results: list[DetectorResult], provider_name: str) -> float | None:
    for result in results:
        if result.provider_name == provider_name and result.available:
            return result.score
    return None


def _preservation_constraints(text: str, semantic: SemanticRepresentation | None) -> list[str]:
    citations = set(extract_citations(text))
    numbers = set(extract_numbers(text))
    terms: set[str] = set()
    if semantic:
        citations.update(semantic.exact_citation_spans)
        numbers.update(semantic.numeric_values)
        terms.update(term for term in semantic.disciplinary_terms if term)
    constraints = ["preserve factual claims and argument structure"]
    if citations:
        constraints.append("preserve citation spans exactly: " + "; ".join(sorted(citations)))
    if numbers:
        constraints.append("preserve numeric values exactly: " + "; ".join(sorted(numbers)))
    if terms:
        constraints.append("preserve disciplinary terminology: " + "; ".join(sorted(terms)[:12]))
    return constraints


def build_refinement_diagnostics(
    *,
    original_text: str,
    current_text: str,
    score_card: ScoreCard,
    detector_results: list[DetectorResult],
    semantic: SemanticRepresentation | None = None,
    baseline_detector_results: list[DetectorResult] | None = None,
) -> RefinementDiagnostics:
    stylometry = _stylometry(current_text)
    failure_modes: list[str] = []
    recommendations: list[str] = []

    fast_score = _score_by_provider(detector_results, "official_fast_detectgpt")
    baseline_fast_score = _score_by_provider(baseline_detector_results or [], "official_fast_detectgpt")
    detector_interpretation: dict[str, Any] = {
        "aggregate_detector_risk": score_card.detector_risk_score,
        "aggregate_label": score_card.detector_label_consensus,
        "detector_disagreement": score_card.detector_disagreement,
    }
    if fast_score is not None:
        detector_interpretation["official_fast_detectgpt"] = {"score": fast_score}
        if baseline_fast_score is not None:
            detector_interpretation["official_fast_detectgpt"]["delta_from_baseline"] = round(fast_score - baseline_fast_score, 4)
        if fast_score >= 0.70:
            failure_modes.append("fast_detectgpt_elevated_artificiality_risk")
            recommendations.append("reduce predictable phrasing by adding locally grounded, discipline-specific reasoning")
        elif fast_score >= 0.55:
            failure_modes.append("fast_detectgpt_borderline_artificiality_risk")
            recommendations.append("make small rhythm and specificity improvements without broad paraphrase")

    if score_card.detector_risk_score >= 0.62 and "aggregate_elevated_artificiality_risk" not in failure_modes:
        failure_modes.append("aggregate_elevated_artificiality_risk")
    if stylometry["low_specificity_risk"] >= 0.70:
        failure_modes.append("low_local_specificity")
        recommendations.append("add concrete linkage between claims already present in the text without inventing evidence")
    if stylometry["repetition_risk"] >= 0.18 or score_card.naturalness_diagnostics.get("repetitive_structure_risk", 0.0) > 0.08:
        failure_modes.append("lexical_or_structural_repetition")
        recommendations.append("replace repeated scaffolding with more precise local phrasing")
    if stylometry["formulaic_transition_density"] >= 0.16:
        failure_modes.append("formulaic_academic_transitions")
        recommendations.append("remove stock transitions and connect sentences through the actual argument")
    if stylometry["uniform_rhythm_risk"] >= 0.62:
        failure_modes.append("uniform_sentence_rhythm")
        recommendations.append("vary sentence length and syntactic shape while preserving meaning")
    if score_card.naturalness_diagnostics.get("generic_llm_pattern_risk", 0.0) >= 0.58:
        failure_modes.append("generic_llm_pattern_risk")
        recommendations.append("prefer specific nouns, concrete relations, and qualified claims over generic academic filler")
    if score_card.hard_constraint_failures:
        failure_modes.append("preservation_gate_failure")
        recommendations.append("restore missing citations, numbers, terms, or other hard preservation items before style changes")

    if not failure_modes:
        failure_modes.append("minor_style_polish_only")
        recommendations.append("make only minimal clarity edits; current diagnostics do not justify broad rewriting")

    seen: set[str] = set()
    unique_recommendations = []
    for recommendation in recommendations:
        if recommendation not in seen:
            seen.add(recommendation)
            unique_recommendations.append(recommendation)

    return RefinementDiagnostics(
        failure_modes=failure_modes,
        detector_interpretation=detector_interpretation,
        rewrite_recommendations=unique_recommendations,
        preservation_constraints=_preservation_constraints(original_text, semantic),
        change_budget={
            "scope": "paragraph-local or sentence-local edits",
            "max_word_delta_ratio": 0.18,
            "allow_reordering": False,
            "allow_new_evidence": False,
            "preserve_citations": True,
        },
        stylometry=stylometry,
    )


def render_refinement_prompt_context(diagnostics: RefinementDiagnostics) -> str:
    return (
        "DIAGNOSTIC_REWRITE_PLAN:\n"
        f"Failure modes: {', '.join(diagnostics.failure_modes)}\n"
        f"Recommendations: {'; '.join(diagnostics.rewrite_recommendations)}\n"
        f"Preservation constraints: {'; '.join(diagnostics.preservation_constraints)}\n"
        f"Change budget: {diagnostics.change_budget}\n"
        "Use the diagnostics as quality guidance. Do not optimize by degrading readability, adding noise, "
        "inventing evidence, changing citations, or changing the author's claims."
    )


def targeted_diagnostic_improvement(before: RefinementDiagnostics, after: RefinementDiagnostics) -> float:
    gains: list[float] = []
    if "uniform_sentence_rhythm" in before.failure_modes:
        gains.append(before.stylometry.get("uniform_rhythm_risk", 0.0) - after.stylometry.get("uniform_rhythm_risk", 0.0))
    if "lexical_or_structural_repetition" in before.failure_modes:
        gains.append(before.stylometry.get("repetition_risk", 0.0) - after.stylometry.get("repetition_risk", 0.0))
    if "formulaic_academic_transitions" in before.failure_modes:
        gains.append(
            before.stylometry.get("formulaic_transition_density", 0.0)
            - after.stylometry.get("formulaic_transition_density", 0.0)
        )
    if "low_local_specificity" in before.failure_modes:
        gains.append(before.stylometry.get("low_specificity_risk", 0.0) - after.stylometry.get("low_specificity_risk", 0.0))
    if "generic_llm_pattern_risk" in before.failure_modes:
        gains.append(after.stylometry.get("lexical_diversity", 0.0) - before.stylometry.get("lexical_diversity", 0.0))
    positive_gains = [gain for gain in gains if gain > 0]
    if not positive_gains:
        return 0.0
    return round(clamp(sum(positive_gains) / len(positive_gains)), 4)
