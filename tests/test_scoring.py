from academic_engine.detectors import HeuristicDetectorProvider
from academic_engine.schemas import DetectorResult, ProviderKind, SemanticRepresentation
from academic_engine.scoring import detector_consensus, hard_constraint_failures, score_candidate
from academic_engine.utils import extract_citations


def test_scoring_weighted_quality_math():
    card = score_candidate(
        original_text="Smith (2021) found a 12% change in policy support.",
        revised_text="More precisely, Smith (2021) found a 12% change in policy support.",
        semantic=SemanticRepresentation(exact_citation_spans=["Smith (2021)"], numeric_values=["12%"]),
        detector_results=[HeuristicDetectorProvider().analyze("More precisely, Smith (2021) found a 12% change in policy support.")],
        risk_flags=[],
    )

    expected = (
        0.28 * card.semantic_fidelity
        + 0.22 * card.factual_consistency
        + 0.15 * card.academic_authenticity
        + 0.12 * card.logical_flow_cohesion
        + 0.10 * card.academic_tone_quality
        + 0.08 * card.clarity_readability
        + 0.05 * card.stylistic_sophistication
    )
    assert card.weighted_quality == round(expected, 4)


def test_citation_and_number_preservation_are_hard_gates():
    failures = hard_constraint_failures(
        "Smith (2021) found a 12% change.",
        "The study found a change.",
        SemanticRepresentation(exact_citation_spans=["Smith (2021)"], numeric_values=["12%"]),
    )

    assert "missing citation span: Smith (2021)" in failures
    assert "missing numeric value: 12%" in failures


def test_extract_citations_handles_narrative_and_parenthetical_forms():
    text = "Smith (2021) argues this point, while later work reaches a similar conclusion (Jones, 2022)."

    assert "Smith (2021)" in extract_citations(text)
    assert "(Jones, 2022)" in extract_citations(text)


def test_detector_consensus_uses_available_signals_and_disagreement():
    results = [
        DetectorResult(
            provider_name="local_stylometry_burstiness",
            provider_kind=ProviderKind.heuristic,
            label="lower_risk",
            score=0.2,
            confidence=0.8,
            input_hash="x",
        ),
        DetectorResult(
            provider_name="local_repetition_genericity",
            provider_kind=ProviderKind.heuristic,
            label="elevated_risk",
            score=0.9,
            confidence=0.8,
            input_hash="x",
        ),
        DetectorResult(
            provider_name="hf_roberta_base_openai_detector",
            provider_kind=ProviderKind.local_model,
            available=False,
            label="unavailable",
            score=0.0,
            confidence=0.0,
            error="not cached",
            input_hash="x",
        ),
    ]

    risk, consensus, disagreement, notes = detector_consensus(results)

    assert 0.2 < risk < 0.9
    assert consensus in {"lower_risk", "elevated_risk"}
    assert disagreement == 0.7
    assert any("Unavailable optional detector" in note for note in notes)


def test_detector_consensus_weights_community_above_heuristics():
    results = [
        DetectorResult(
            provider_name="local_repetition_genericity",
            provider_kind=ProviderKind.heuristic,
            label="lower_risk",
            score=0.1,
            confidence=1.0,
            input_hash="x",
        ),
        DetectorResult(
            provider_name="community_binoculars",
            provider_kind=ProviderKind.local_model,
            label="elevated_risk",
            score=0.9,
            confidence=1.0,
            input_hash="x",
        ),
    ]

    risk, consensus, _, notes = detector_consensus(results)

    assert risk > 0.65
    assert consensus == "elevated_risk"
    assert any("Community detector signals weighted strongly" in note for note in notes)


def test_detector_consensus_weights_official_above_heuristics():
    results = [
        DetectorResult(
            provider_name="local_repetition_genericity",
            provider_kind=ProviderKind.heuristic,
            label="lower_risk",
            score=0.1,
            confidence=1.0,
            input_hash="x",
        ),
        DetectorResult(
            provider_name="official_fast_detectgpt",
            provider_kind=ProviderKind.local_model,
            label="elevated_risk",
            score=0.9,
            confidence=1.0,
            input_hash="x",
        ),
    ]

    risk, consensus, _, notes = detector_consensus(results)

    assert risk > 0.65
    assert consensus == "elevated_risk"
    assert any("Official detector signals weighted strongly" in note for note in notes)
