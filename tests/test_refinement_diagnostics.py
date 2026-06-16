from academic_engine.detectors import detector_result
from academic_engine.refinement_diagnostics import (
    build_refinement_diagnostics,
    render_refinement_prompt_context,
    targeted_diagnostic_improvement,
)
from academic_engine.schemas import ProviderKind, ScoreCard, SemanticRepresentation


def make_score(detector_risk: float = 0.82) -> ScoreCard:
    return ScoreCard.compute(
        semantic_fidelity=0.94,
        factual_consistency=0.92,
        academic_authenticity=0.68,
        logical_flow_cohesion=0.72,
        academic_tone_quality=0.74,
        clarity_readability=0.76,
        stylistic_sophistication=0.65,
        detector_risk_score=detector_risk,
        detector_label_consensus="elevated_risk",
        detector_disagreement=0.12,
        false_positive_risk_notes=[],
        hard_constraint_failures=[],
        naturalness_diagnostics={"generic_llm_pattern_risk": 0.61, "repetitive_structure_risk": 0.11},
        non_disruptive_edit_score=0.9,
    )


def test_refinement_diagnostics_interprets_fast_detectgpt_and_preservation_constraints():
    original = "Smith (2021) found a 12% change in media trust."
    current = (
        "It is important to note that Smith (2021) found a 12% change in media trust. "
        "Furthermore, this highlights the importance of media trust."
    )
    detectors = [
        detector_result(
            provider_name="official_fast_detectgpt",
            provider_kind=ProviderKind.local_model,
            score=0.85,
            confidence=0.91,
            raw_result={"ai_probability": 0.85},
            text=current,
        )
    ]
    semantic = SemanticRepresentation(
        exact_citation_spans=["Smith (2021)"],
        numeric_values=["12%"],
        disciplinary_terms=["media trust"],
    )

    diagnostics = build_refinement_diagnostics(
        original_text=original,
        current_text=current,
        score_card=make_score(),
        detector_results=detectors,
        semantic=semantic,
    )

    assert "fast_detectgpt_elevated_artificiality_risk" in diagnostics.failure_modes
    assert "generic_llm_pattern_risk" in diagnostics.failure_modes
    assert diagnostics.detector_interpretation["official_fast_detectgpt"]["score"] == 0.85
    assert any("Smith (2021)" in constraint for constraint in diagnostics.preservation_constraints)
    assert any("12%" in constraint for constraint in diagnostics.preservation_constraints)
    assert diagnostics.change_budget["allow_new_evidence"] is False


def test_render_refinement_prompt_context_is_json_prompt_safe():
    diagnostics = build_refinement_diagnostics(
        original_text="The study reports a measured result.",
        current_text="The study reports a measured result.",
        score_card=make_score(detector_risk=0.2),
        detector_results=[],
    )

    rendered = render_refinement_prompt_context(diagnostics)

    assert "DIAGNOSTIC_REWRITE_PLAN" in rendered
    assert "Do not optimize by degrading readability" in rendered
    assert "Return JSON only" not in rendered


def test_targeted_diagnostic_improvement_rewards_addressed_failure_mode():
    score = make_score(detector_risk=0.3)
    before = build_refinement_diagnostics(
        original_text="Smith (2021) reports a 12% change. This result matters.",
        current_text="Smith (2021) reports a 12% change. This result matters.",
        score_card=score,
        detector_results=[],
    )
    before.failure_modes = ["uniform_sentence_rhythm"]
    before.stylometry["uniform_rhythm_risk"] = 0.8
    after = before.model_copy(deep=True)
    after.stylometry["uniform_rhythm_risk"] = 0.4

    assert targeted_diagnostic_improvement(before, after) == 0.4
