from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Strategy(str, Enum):
    conservative_academic = "conservative_academic"
    natural_scholarly = "natural_scholarly"
    enhanced_clarity = "enhanced_clarity"
    structural_optimization = "structural_optimization"
    stylistic_maturation = "stylistic_maturation"
    non_native_refinement = "non_native_refinement"
    precision_oriented = "precision_oriented"


class ProviderKind(str, Enum):
    api = "api"
    browser = "browser"
    manual = "manual"
    heuristic = "heuristic"
    local_model = "local_model"


class FailureMode(str, Enum):
    citation_drift = "citation_drift"
    numeric_drift = "numeric_drift"
    terminology_drift = "terminology_drift"
    semantic_drift = "semantic_drift"
    argument_structure_drift = "argument_structure_drift"
    high_artificiality_risk = "high_artificiality_risk"
    low_naturalness = "low_naturalness"
    low_specificity = "low_specificity"
    detector_unavailable = "detector_unavailable"
    runpod_unavailable = "runpod_unavailable"
    malformed_detector_response = "malformed_detector_response"
    timeout = "timeout"
    hard_gate_failure = "hard_gate_failure"


class NormalizedInput(BaseModel):
    original_text: str
    normalized_text: str
    language: str
    document_type: str
    paragraphs: list[str]
    warnings: list[str] = Field(default_factory=list)

    @field_validator("normalized_text")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input text is empty")
        return value


class SemanticRepresentation(BaseModel):
    claims: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    disciplinary_terms: list[str] = Field(default_factory=list)
    citations_or_references: list[str] = Field(default_factory=list)
    exact_citation_spans: list[str] = Field(default_factory=list)
    numeric_values: list[str] = Field(default_factory=list)
    argument_structure: list[str] = Field(default_factory=list)
    uncertainty_markers: list[str] = Field(default_factory=list)
    non_negotiable_preservation_items: list[str] = Field(default_factory=list)


class AcademicProfile(BaseModel):
    discipline: str
    subdiscipline: str = "inferred"
    document_type: str
    audience: str = "academic"
    writing_level: str = "undergraduate"
    author_needs: list[str] = Field(default_factory=list)
    style_constraints: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)


class CandidateRevision(BaseModel):
    candidate_id: str
    rewritten_text: str
    strategy: Strategy
    intended_improvements: list[str] = Field(default_factory=list)
    preservation_notes: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class DetectorResult(BaseModel):
    provider_name: str
    provider_kind: ProviderKind
    available: bool = True
    label: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_hash: str


class DetectorSignal(BaseModel):
    detector: str
    available: bool = True
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    label: str = "unavailable"
    raw_result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ClusteredDetectorSignal(BaseModel):
    cluster: str
    members: list[DetectorSignal] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    median_score: float = Field(default=0.0, ge=0.0, le=1.0)
    disagreement: float = Field(default=0.0, ge=0.0, le=1.0)
    unavailable_members: list[str] = Field(default_factory=list)


class DetectorPartialFailure(BaseModel):
    scope: str
    detector: str | None = None
    item_id: str | None = None
    failure_mode: FailureMode
    message: str


class DetectorBatchText(BaseModel):
    id: str
    text: str
    source: str | None = None
    candidate_id: str | None = None


class DetectorBatchRequest(BaseModel):
    operation: str = "score_batch"
    profile: str = "stable"
    texts: list[DetectorBatchText]
    detectors: list[str] | None = None
    max_length: int = 512
    request_id: str
    return_raw: bool = False


class DetectorBatchResult(BaseModel):
    id: str
    candidate_id: str | None = None
    signals: list[DetectorSignal] = Field(default_factory=list)
    clustered_signals: list[ClusteredDetectorSignal] = Field(default_factory=list)
    raw_detector_results: dict[str, Any] = Field(default_factory=dict)
    detector_disagreement: float = Field(default=0.0, ge=0.0, le=1.0)
    artificiality_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class DetectorBatchTelemetry(BaseModel):
    total_seconds: float = 0.0
    model_load_seconds: dict[str, float] = Field(default_factory=dict)
    inference_seconds: dict[str, float] = Field(default_factory=dict)
    batch_size: int = 0


class DetectorBatchResponse(BaseModel):
    request_id: str
    profile: str
    device: str = "unavailable"
    results: list[DetectorBatchResult] = Field(default_factory=list)
    timing: DetectorBatchTelemetry = Field(default_factory=DetectorBatchTelemetry)
    loaded_models: list[str] = Field(default_factory=list)
    errors: list[DetectorPartialFailure] = Field(default_factory=list)


class ExcludedCandidateAudit(BaseModel):
    candidate_id: str
    strategy: str
    text: str
    scores: dict[str, Any]
    hard_constraint_failures: list[str] = Field(default_factory=list)
    exclusion_reasons: list[str] = Field(default_factory=list)
    failure_modes: list[FailureMode] = Field(default_factory=list)


class ScoreCard(BaseModel):
    semantic_fidelity: float = Field(ge=0.0, le=1.0)
    factual_consistency: float = Field(ge=0.0, le=1.0)
    academic_authenticity: float = Field(ge=0.0, le=1.0)
    logical_flow_cohesion: float = Field(ge=0.0, le=1.0)
    academic_tone_quality: float = Field(ge=0.0, le=1.0)
    clarity_readability: float = Field(ge=0.0, le=1.0)
    stylistic_sophistication: float = Field(ge=0.0, le=1.0)
    detector_risk_score: float = Field(ge=0.0, le=1.0)
    detector_label_consensus: str
    detector_disagreement: float = Field(ge=0.0, le=1.0)
    false_positive_risk_notes: list[str] = Field(default_factory=list)
    hard_constraint_failures: list[str] = Field(default_factory=list)
    naturalness_diagnostics: dict[str, float] = Field(default_factory=dict)
    weighted_quality: float = Field(ge=0.0, le=1.0)
    candidate_utility: float = Field(ge=0.0, le=1.0)

    @classmethod
    def compute(
        cls,
        *,
        semantic_fidelity: float,
        factual_consistency: float,
        academic_authenticity: float,
        logical_flow_cohesion: float,
        academic_tone_quality: float,
        clarity_readability: float,
        stylistic_sophistication: float,
        detector_risk_score: float,
        detector_label_consensus: str,
        detector_disagreement: float,
        false_positive_risk_notes: list[str],
        hard_constraint_failures: list[str],
        naturalness_diagnostics: dict[str, float],
        non_disruptive_edit_score: float,
    ) -> "ScoreCard":
        weighted_quality = (
            0.28 * semantic_fidelity
            + 0.22 * factual_consistency
            + 0.15 * academic_authenticity
            + 0.12 * logical_flow_cohesion
            + 0.10 * academic_tone_quality
            + 0.08 * clarity_readability
            + 0.05 * stylistic_sophistication
        )
        preservation_safety = min(semantic_fidelity, factual_consistency)
        if hard_constraint_failures:
            preservation_safety = min(preservation_safety, 0.25)
        detector_false_positive_robustness = 1.0 - detector_risk_score
        candidate_utility = (
            0.45 * preservation_safety
            + 0.25 * weighted_quality
            + 0.20 * detector_false_positive_robustness
            + 0.10 * non_disruptive_edit_score
        )
        return cls(
            semantic_fidelity=semantic_fidelity,
            factual_consistency=factual_consistency,
            academic_authenticity=academic_authenticity,
            logical_flow_cohesion=logical_flow_cohesion,
            academic_tone_quality=academic_tone_quality,
            clarity_readability=clarity_readability,
            stylistic_sophistication=stylistic_sophistication,
            detector_risk_score=detector_risk_score,
            detector_label_consensus=detector_label_consensus,
            detector_disagreement=detector_disagreement,
            false_positive_risk_notes=false_positive_risk_notes,
            hard_constraint_failures=hard_constraint_failures,
            naturalness_diagnostics=naturalness_diagnostics,
            weighted_quality=round(weighted_quality, 4),
            candidate_utility=round(candidate_utility, 4),
        )


class RankedCandidate(BaseModel):
    candidate: CandidateRevision
    detector_results: list[DetectorResult]
    score_card: ScoreCard
    rank: int
    passed_hard_constraints: bool


class RefinementCycle(BaseModel):
    cycle_number: int
    starting_candidate_id: str
    refined_candidate: CandidateRevision
    detector_results: list[DetectorResult]
    score_card: ScoreCard
    notes: list[str] = Field(default_factory=list)
    diagnostic_context: dict[str, Any] = Field(default_factory=dict)
    accepted_for_next_cycle: bool = True


class RevisionReport(BaseModel):
    refined_text: str
    major_revisions: list[str]
    semantic_preservation_analysis: dict[str, Any]
    academic_quality_analysis: dict[str, Any]
    style_analysis: dict[str, Any]
    detector_signal_analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    optional_detector_audit: list[DetectorResult] = Field(default_factory=list)
    excluded_candidate_audit: list[ExcludedCandidateAudit] = Field(default_factory=list)


class PipelineResult(BaseModel):
    run_id: str
    input_path: str | None = None
    normalized_input: NormalizedInput
    semantic_representation: SemanticRepresentation
    academic_profile: AcademicProfile
    candidates: list[CandidateRevision]
    ranked_candidates: list[RankedCandidate]
    refinement_cycles: list[RefinementCycle]
    final_report: RevisionReport
    artifact_path: str | None = None

    @model_validator(mode="after")
    def has_strategy_coverage(self) -> "PipelineResult":
        if len({candidate.strategy for candidate in self.candidates}) < 5:
            raise ValueError("pipeline result must include at least five candidate strategies")
        return self


class ExperimentFixtureResult(BaseModel):
    fixture_path: str
    before_detector_risk: float
    after_detector_risk: float
    final_quality: float
    utility: float
    non_disruptive_change_score: float
    preservation_warnings: list[str]
    hard_constraint_failures: list[str]
    artifact_path: str | None


class ExperimentSummary(BaseModel):
    fixture_dir: str
    fixture_count: int
    average_before_detector_risk: float
    average_after_detector_risk: float
    average_final_quality: float
    average_non_disruptive_change_score: float
    results: list[ExperimentFixtureResult]
    artifact_path: str | None = None


class RewriteJob(BaseModel):
    input_path: Path
    output_path: Path
    max_refinement_cycles: int = Field(default=2, ge=1, le=2)
    mock_provider: bool = False
