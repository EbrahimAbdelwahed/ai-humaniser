from dataclasses import replace
from pathlib import Path

from academic_engine.config import EngineConfig
from academic_engine.detectors import DetectorProvider, detector_result
from academic_engine.pipeline import AcademicRewritePipeline
from academic_engine.schemas import CandidateRevision, ProviderKind, Strategy


class UnsafeRefinementProvider:
    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        if schema_name == "RefinedCandidate":
            return CandidateRevision(
                candidate_id="unsafe",
                rewritten_text="The rewritten text drops the citation and number.",
                strategy=Strategy.natural_scholarly,
                intended_improvements=["reduce detector-risk markers"],
                preservation_notes=[],
                risk_flags=[],
            ).model_dump(mode="json")
        return DeterministicMockProvider().complete_json(system=system, user=user, schema_name=schema_name)


class NestedSchemaProvider:
    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        payload = DeterministicMockProvider().complete_json(system=system, user=user, schema_name=schema_name)
        wrappers = {
            "SemanticRepresentation": "semantic_representation",
            "AcademicProfile": "academic_profile",
            "CandidateRevisions": "candidate_revisions",
            "CandidateRevision": "candidate_revision",
            "RefinedCandidate": "refined_candidate",
        }
        return {wrappers[schema_name]: payload}


class SingleCandidateCountingProvider:
    def __init__(self) -> None:
        self.single_candidate_calls: list[str] = []

    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        if schema_name == "CandidateRevision":
            strategy = next(line.split(":", 1)[1].strip() for line in user.splitlines() if line.startswith("STRATEGY:"))
            self.single_candidate_calls.append(strategy)
        return DeterministicMockProvider().complete_json(system=system, user=user, schema_name=schema_name)


class AllUnsafeCandidateProvider:
    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        if schema_name == "CandidateRevision":
            strategy = next(line.split(":", 1)[1].strip() for line in user.splitlines() if line.startswith("STRATEGY:"))
            candidate_id = next(line.split(":", 1)[1].strip() for line in user.splitlines() if line.startswith("CANDIDATE_ID:"))
            return CandidateRevision(
                candidate_id=candidate_id,
                rewritten_text="This generated candidate drops the required citation and numeric value.",
                strategy=Strategy(strategy),
                intended_improvements=["shorten and smooth the prose"],
                preservation_notes=[],
                risk_flags=[],
            ).model_dump(mode="json")
        return DeterministicMockProvider().complete_json(system=system, user=user, schema_name=schema_name)


class DiagnosticImprovingProvider:
    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        mock = DeterministicMockProvider()
        if schema_name == "RefinedCandidate":
            text = mock.extract_text(user)
            for prefix in [
                "This passage can be stated more carefully:",
                "The argument can be expressed in a measured scholarly voice:",
                "The central point can be clarified as follows:",
                "Organized around its main claim, the passage argues that",
                "In a more mature academic register, the passage indicates that",
                "With smoother academic phrasing, the passage explains that",
                "More precisely, the passage maintains that",
            ]:
                text = text.replace(prefix, "").strip()
            return CandidateRevision(
                candidate_id="diagnostic-refined",
                rewritten_text=text,
                strategy=Strategy.natural_scholarly,
                intended_improvements=["remove formulaic scaffolding", "preserve the original claim"],
                preservation_notes=["citation spans and numeric values are preserved"],
                risk_flags=[],
            ).model_dump(mode="json")
        return mock.complete_json(system=system, user=user, schema_name=schema_name)


class StringListRefinementProvider:
    def complete_json(self, *, system: str, user: str, schema_name: str):
        from academic_engine.llm import DeterministicMockProvider

        mock = DeterministicMockProvider()
        if schema_name == "RefinedCandidate":
            text = mock.extract_text(user)
            return {
                "candidate_id": "string-list-refined",
                "rewritten_text": text,
                "strategy": "natural_scholarly",
                "intended_improvements": "Improved specificity while preserving the argument.",
                "preservation_notes": "Preserved citations and numbers.",
                "risk_flags": "",
            }
        return mock.complete_json(system=system, user=user, schema_name=schema_name)


class CountingTeacherDetector(DetectorProvider):
    provider_name = "flash_binoculars"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def analyze(self, text: str):
        self.calls.append(text)
        return detector_result(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.api,
            score=0.41,
            confidence=0.9,
            raw_result={"mock": True},
            text=text,
        )


class CountingBatchTeacherDetector(DetectorProvider):
    provider_name = "flash_roberta_cluster"

    def __init__(self) -> None:
        self.batch_calls: list[list[str]] = []

    def analyze(self, text: str):
        raise AssertionError("batch teacher should not be called per candidate")

    def analyze_batch(self, texts):
        self.batch_calls.append([item_id for item_id, _ in texts])
        return {
            item_id: [
                detector_result(
                    provider_name=self.provider_name,
                    provider_kind=ProviderKind.api,
                    score=0.37,
                    confidence=0.88,
                    raw_result={"cluster": "roberta_cluster", "mock": True},
                    text=text,
                )
            ]
            for item_id, text in texts
        }


class CountingLocalDetector(DetectorProvider):
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        self.calls = 0

    def analyze(self, text: str):
        self.calls += 1
        return detector_result(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.heuristic,
            score=0.3,
            confidence=0.8,
            raw_result={"mock": True},
            text=text,
        )


class FormulaicPrefixDetector(DetectorProvider):
    provider_name = "official_fast_detectgpt"

    def analyze(self, text: str):
        formulaic = any(
            marker in text
            for marker in [
                "This passage can be stated",
                "The argument can be expressed",
                "The central point can be clarified",
                "Organized around its main claim",
                "In a more mature academic register",
                "With smoother academic phrasing",
                "More precisely, the passage maintains",
            ]
        )
        return detector_result(
            provider_name=self.provider_name,
            provider_kind=ProviderKind.local_model,
            score=0.86 if formulaic else 0.22,
            confidence=0.95,
            raw_result={"mock": True, "formulaic_prefix": formulaic},
            text=text,
            label="elevated_risk" if formulaic else "lower_risk",
        )


def test_pipeline_contract_preserves_citations_and_has_stages(tmp_path):
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    pipeline = AcademicRewritePipeline(config=EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1))

    result = pipeline.run_text(text)

    assert len({candidate.strategy for candidate in result.candidates}) >= 5
    assert result.ranked_candidates
    assert "Smith (2021)" in result.final_report.refined_text
    assert "Return JSON only" not in result.final_report.refined_text
    assert result.final_report.detector_signal_analysis["caveat"]
    assert len(result.ranked_candidates[0].detector_results) >= 3
    assert result.final_report.detector_signal_analysis["detectors"]
    assert result.final_report.detector_signal_analysis["label_consensus"]
    quality = result.final_report.academic_quality_analysis
    assert quality["selected_candidate"]["candidate_id"]
    assert "detector_disagreement" in quality["selected_candidate"]
    assert quality["stop_reason"]
    assert quality["refinement_loop"][0]["detector_risk_score"] >= 0
    assert quality["refinement_loop"][0]["constraint_failures"] == []
    assert quality["non_disruptive_change_summary"]["preservation_gate"] == "passed"
    assert result.artifact_path is not None


def test_detector_results_parallel_uses_explicit_provider_subset(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="local", env_file=tmp_path / "missing.env")
    config = replace(config, detector_execution_mode="parallel", detector_concurrency=2)
    first = CountingLocalDetector("first")
    second = CountingLocalDetector("second")
    pipeline = AcademicRewritePipeline(config=config, detector_providers=[first, second])

    results = pipeline.detector_results("Smith (2021) found a 12% change.", providers=[first])

    assert [result.provider_name for result in results] == ["first"]
    assert first.calls == 1
    assert second.calls == 0


def test_pipeline_accepts_nested_provider_schema_payloads():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    pipeline = AcademicRewritePipeline(config=config, llm_provider=NestedSchemaProvider())

    result = pipeline.run_text(text, write_artifact=False)

    assert result.academic_profile.discipline
    assert result.ranked_candidates
    assert result.final_report.academic_quality_analysis["selected_candidate"]["candidate_id"]


def test_candidate_generation_requests_one_candidate_per_strategy():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    provider = SingleCandidateCountingProvider()
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    pipeline = AcademicRewritePipeline(config=config, llm_provider=provider)

    result = pipeline.run_text(text, write_artifact=False)

    assert len(result.candidates) == 7
    assert len(provider.single_candidate_calls) == 7
    assert len(set(provider.single_candidate_calls)) == 7


def test_pipeline_preserves_original_when_all_generated_candidates_fail_hard_gates():
    text = "Smith (2021) found a 12% change in policy support among students."
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    pipeline = AcademicRewritePipeline(config=config, llm_provider=AllUnsafeCandidateProvider())

    result = pipeline.run_text(text, write_artifact=False)
    quality = result.final_report.academic_quality_analysis

    assert result.final_report.refined_text == text
    assert quality["selected_candidate"]["candidate_id"] == "preservation-fallback-original"
    assert quality["selected_candidate"]["source"] == "preservation_fallback"
    assert quality["stop_reason"] == "blocked_no_safe_candidate_preserved_original"
    assert quality["non_disruptive_change_summary"]["preservation_gate"] == "passed"
    assert "No generated candidate passed hard preservation gates" in " ".join(result.final_report.warnings)


def test_pipeline_local_plus_community_runs_when_community_unavailable():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1, detector_set="local+community")
    pipeline = AcademicRewritePipeline(config=config)

    result = pipeline.run_text(text, write_artifact=False)
    analysis = result.final_report.detector_signal_analysis

    assert result.ranked_candidates
    assert analysis["community_detectors"] == ["community_binoculars", "community_ghostbuster", "community_mage", "community_radar"]
    assert len(analysis["unavailable_detectors"]) >= 4
    assert "Smith (2021)" in result.final_report.refined_text


def test_calibration_mode_audits_all_candidates_with_teacher_detector(tmp_path):
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1, detector_set="local+flash", env_file=tmp_path / "missing.env")
    config = replace(config, flash_mode="calibration", quality_threshold=1.0, detector_risk_target=0.0)
    teacher = CountingTeacherDetector()
    pipeline = AcademicRewritePipeline(config=config, detector_providers=[])
    pipeline.detectors = pipeline.detectors + [teacher]

    result = pipeline.run_text(text, write_artifact=False)

    assert len(result.ranked_candidates) == 7
    assert len(teacher.calls) >= 7
    assert all(any(detector.provider_name == "flash_binoculars" for detector in item.detector_results) for item in result.ranked_candidates)


def test_pipeline_scores_multiple_candidates_with_one_batch_teacher_call(tmp_path):
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1, detector_set="flash", env_file=tmp_path / "missing.env")
    config = replace(config, flash_mode="calibration")
    teacher = CountingBatchTeacherDetector()
    pipeline = AcademicRewritePipeline(config=config, detector_providers=[teacher])

    result = pipeline.run_text(text, write_artifact=False)

    assert len(result.ranked_candidates) == 7
    assert len(teacher.batch_calls) == 1
    assert len(teacher.batch_calls[0]) == 7
    assert all(any(detector.provider_name == "flash_roberta_cluster" for detector in item.detector_results) for item in result.ranked_candidates)


def test_calibration_artifact_shape(tmp_path):
    input_path = Path("tests/fixtures/political_science.txt")
    output_path = tmp_path / "calibration.json"
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1, detector_set="local+flash", env_file=tmp_path / "missing.env")
    config = replace(config, flash_mode="calibration")
    pipeline = AcademicRewritePipeline(config=config)

    artifact = pipeline.calibration_audit(input_path, output_path)

    assert output_path.exists()
    assert artifact["artifact_type"] == "academic_engine_calibration_audit"
    assert artifact["teacher_detector_policy"] == "all_candidates"
    assert len(artifact["candidate_audits"]) == 7
    first = artifact["candidate_audits"][0]
    assert {
        "candidate_id",
        "strategy",
        "prompt_metadata",
        "detector_scores",
        "preservation_quality",
        "winner",
        "failure_notes",
        "exclusion_reasons",
        "failure_modes",
    } <= set(first)
    assert any(detector["provider_name"].startswith("flash_") for detector in first["detector_scores"])


def test_report_persists_excluded_candidate_audit():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    pipeline = AcademicRewritePipeline(config=EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1))

    result = pipeline.run_text(text, write_artifact=False)

    selected_id = result.final_report.academic_quality_analysis["selected_candidate"]["candidate_id"]
    audit = result.final_report.excluded_candidate_audit
    assert audit
    assert selected_id not in {item.candidate_id for item in audit}
    assert {
        "candidate_id",
        "strategy",
        "text",
        "scores",
        "hard_constraint_failures",
        "exclusion_reasons",
        "failure_modes",
    } <= set(audit[0].model_dump(mode="json"))


def test_experiment_summary_runs_multiple_fixtures():
    pipeline = AcademicRewritePipeline(config=EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1))

    summary = pipeline.experiment(Path("tests/fixtures"))

    assert summary.fixture_count >= 4
    assert summary.average_final_quality > 0
    assert summary.artifact_path is not None


def test_final_selection_rejects_unsafe_refinement():
    text = "Smith (2021) found a 12% change in policy support among students."
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    config = replace(
        config,
        max_refinement_cycles=1,
        quality_threshold=1.0,
        detector_risk_target=0.0,
    )
    pipeline = AcademicRewritePipeline(config=config, llm_provider=UnsafeRefinementProvider())

    result = pipeline.run_text(text, write_artifact=False)

    assert "Smith (2021)" in result.final_report.refined_text
    assert "12%" in result.final_report.refined_text
    assert result.refinement_cycles[0].score_card.hard_constraint_failures
    quality = result.final_report.academic_quality_analysis
    assert quality["stop_reason"] == "stopped_after_hard_constraint_failure"
    assert quality["selected_candidate"]["source"] == "ranked_candidate"
    assert quality["refinement_loop"][1]["constraint_failures"]


def test_refinement_cycles_include_diagnostic_context():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    config = replace(
        config,
        max_refinement_cycles=1,
        quality_threshold=1.0,
        detector_risk_target=0.0,
    )
    pipeline = AcademicRewritePipeline(config=config)

    result = pipeline.run_text(text, write_artifact=False)
    quality = result.final_report.academic_quality_analysis

    assert result.refinement_cycles
    cycle = result.refinement_cycles[0]
    assert cycle.diagnostic_context["failure_modes"]
    assert "rewrite_recommendations" in cycle.diagnostic_context
    assert quality["diagnostic_refinement"][0]["failure_modes"] == cycle.diagnostic_context["failure_modes"]
    assert "diagnostic_failure_modes" in quality["refinement_loop"][1]
    if not cycle.accepted_for_next_cycle:
        assert quality["selected_candidate"]["candidate_id"] != cycle.refined_candidate.candidate_id
        assert quality["stop_reason"] == "refinement_rejected_no_safe_improvement"


def test_diagnostic_refinement_can_accept_detector_risk_improvement():
    text = "Smith (2021) found a 12% change in policy support among students."
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1, detector_set="official-fast-detectgpt")
    config = replace(
        config,
        max_refinement_cycles=1,
        quality_threshold=1.0,
        detector_risk_target=0.0,
    )
    pipeline = AcademicRewritePipeline(
        config=config,
        llm_provider=DiagnosticImprovingProvider(),
        detector_providers=[FormulaicPrefixDetector()],
    )

    result = pipeline.run_text(text, write_artifact=False)
    quality = result.final_report.academic_quality_analysis

    assert result.refinement_cycles[0].accepted_for_next_cycle is True
    assert quality["selected_candidate"]["source"] == "refinement_cycle"
    assert quality["selected_candidate"]["detector_risk_score"] < quality["refinement_loop"][0]["detector_risk_score"]
    assert "Smith (2021)" in result.final_report.refined_text
    assert "12%" in result.final_report.refined_text


def test_refined_candidate_validation_coerces_string_list_fields():
    text = "Smith (2021) found a 12% change in policy support among students."
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    config = replace(config, quality_threshold=1.0, detector_risk_target=0.0)
    pipeline = AcademicRewritePipeline(config=config, llm_provider=StringListRefinementProvider())

    result = pipeline.run_text(text, write_artifact=False)

    assert result.refinement_cycles
    refined = result.refinement_cycles[0].refined_candidate
    assert refined.intended_improvements == ["Improved specificity while preserving the argument."]
    assert refined.preservation_notes == ["Preserved citations and numbers."]


def test_final_selection_prefers_lower_detector_risk_when_utility_is_close():
    text = Path("tests/fixtures/political_science.txt").read_text(encoding="utf-8")
    config = EngineConfig.from_env(use_mock_provider=True, max_refinement_cycles=1)
    config = replace(
        config,
        max_refinement_cycles=1,
        quality_threshold=1.0,
        detector_risk_target=0.0,
    )
    pipeline = AcademicRewritePipeline(config=config)

    result = pipeline.run_text(text, write_artifact=False)
    quality = result.final_report.academic_quality_analysis

    assert result.refinement_cycles
    assert quality["refinement_loop"][1]["detector_risk_score"] > quality["refinement_loop"][0]["detector_risk_score"]
    assert quality["selected_candidate"]["source"] == "ranked_candidate"
