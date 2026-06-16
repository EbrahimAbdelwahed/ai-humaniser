from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from academic_engine.detector_registry import expand_profile


FLASH_DETECTOR_PROFILES: dict[str, tuple[str, ...]] = {
    "stable": ("roberta_cluster",),
    "model": ("roberta_cluster",),
    "calibration": ("roberta_cluster", "binoculars"),
    "experimental": ("roberta_cluster", "binoculars", "ghostbuster"),
    "all": ("roberta_cluster", "binoculars", "ghostbuster", "mage"),
}


def load_env_file(path: Path = Path(".env")) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class EngineConfig:
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    max_refinement_cycles: int = 2
    quality_threshold: float = 0.72
    detector_risk_target: float = 0.42
    runs_dir: Path = Path("runs")
    use_mock_provider: bool = False
    detector_set: str = "local"
    include_hf_detector: bool = False
    hf_detector_model: str = "openai-community/roberta-base-openai-detector"
    detector_execution_mode: str = "sequential"
    detector_concurrency: int = 1
    candidate_generation_concurrency: int = 1
    community_candidate_limit: int = 2
    binoculars_model_name: str = "tiiuae/falcon-7b"
    binoculars_observer_name: str = "tiiuae/falcon-7b-instruct"
    binoculars_performer_model: str | None = None
    binoculars_performer_base_url: str | None = None
    binoculars_performer_api_key: str | None = None
    binoculars_observer_model: str | None = None
    binoculars_observer_base_url: str | None = None
    binoculars_observer_api_key: str | None = None
    binoculars_cli: str | None = None
    ghostbuster_cli: str | None = None
    mage_cli: str | None = None
    radar_cli: str | None = None
    official_binoculars_cli: str | None = None
    official_ghostbuster_cli: str | None = None
    official_fast_detectgpt_cli: str | None = None
    official_detector_timeout_seconds: int = 300
    official_flash_endpoint_id: str | None = None
    official_flash_timeout_seconds: int = 900
    runpod_api_key: str | None = None
    flash_detector_profile: str = "stable"
    flash_detector_names: tuple[str, ...] = FLASH_DETECTOR_PROFILES["stable"]
    flash_mode: str = "production"
    flash_endpoint_id: str | None = None
    flash_endpoint_ids: dict[str, str] | None = None
    flash_timeout_seconds: int = 120

    @classmethod
    def from_env(
        cls,
        *,
        use_mock_provider: bool | None = None,
        max_refinement_cycles: int | None = None,
        detector_set: str | None = None,
        include_hf_detector: bool | None = None,
        env_file: Path = Path(".env"),
    ) -> "EngineConfig":
        file_values = load_env_file(env_file)
        api_key = os.getenv("DEEPSEEK_API_KEY") or file_values.get("DEEPSEEK_API_KEY") or None
        runpod_api_key = os.getenv("RUNPOD_API_KEY") or file_values.get("RUNPOD_API_KEY") or None
        cycles = max_refinement_cycles or int(os.getenv("ACADEMIC_ENGINE_MAX_CYCLES") or file_values.get("ACADEMIC_ENGINE_MAX_CYCLES", "2"))
        configured_detector_set = detector_set or os.getenv("ACADEMIC_ENGINE_DETECTORS") or file_values.get("ACADEMIC_ENGINE_DETECTORS", "local")
        flash_detector_profile = (
            os.getenv("ACADEMIC_ENGINE_FLASH_PROFILE")
            or file_values.get("ACADEMIC_ENGINE_FLASH_PROFILE", "stable")
        ).lower()
        if flash_detector_profile not in FLASH_DETECTOR_PROFILES:
            flash_detector_profile = "stable"
        configured_flash_detectors = os.getenv("ACADEMIC_ENGINE_FLASH_DETECTORS") or file_values.get("ACADEMIC_ENGINE_FLASH_DETECTORS")
        flash_detector_names = (
            tuple(name.strip().lower() for name in configured_flash_detectors.split(",") if name.strip())
            if configured_flash_detectors
            else expand_profile(flash_detector_profile)
        )
        flash_mode = (
            os.getenv("ACADEMIC_ENGINE_FLASH_MODE")
            or file_values.get("ACADEMIC_ENGINE_FLASH_MODE", "production")
        ).lower()
        if flash_mode not in {"production", "calibration", "research"}:
            flash_mode = "production"
        hf_env = os.getenv("ACADEMIC_ENGINE_INCLUDE_HF_DETECTOR") or file_values.get("ACADEMIC_ENGINE_INCLUDE_HF_DETECTOR", "")
        include_hf = include_hf_detector if include_hf_detector is not None else configured_detector_set in {"local+hf", "hf", "all"} or hf_env.lower() in {"1", "true", "yes", "on"}
        execution_mode = os.getenv("ACADEMIC_ENGINE_DETECTOR_EXECUTION") or file_values.get("ACADEMIC_ENGINE_DETECTOR_EXECUTION", "sequential")
        concurrency = int(os.getenv("ACADEMIC_ENGINE_DETECTOR_CONCURRENCY") or file_values.get("ACADEMIC_ENGINE_DETECTOR_CONCURRENCY", "1"))
        candidate_generation_concurrency = int(
            os.getenv("ACADEMIC_ENGINE_CANDIDATE_GENERATION_CONCURRENCY")
            or file_values.get("ACADEMIC_ENGINE_CANDIDATE_GENERATION_CONCURRENCY", "1")
        )
        community_limit = int(os.getenv("ACADEMIC_ENGINE_COMMUNITY_CANDIDATE_LIMIT") or file_values.get("ACADEMIC_ENGINE_COMMUNITY_CANDIDATE_LIMIT", "2"))
        flash_endpoint_ids = {
            "binoculars": os.getenv("ACADEMIC_ENGINE_FLASH_BINOCULARS_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_BINOCULARS_ENDPOINT_ID", ""),
            "ghostbuster": os.getenv("ACADEMIC_ENGINE_FLASH_GHOSTBUSTER_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_GHOSTBUSTER_ENDPOINT_ID", ""),
            "mage": os.getenv("ACADEMIC_ENGINE_FLASH_MAGE_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_MAGE_ENDPOINT_ID", ""),
            "radar": os.getenv("ACADEMIC_ENGINE_FLASH_RADAR_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_RADAR_ENDPOINT_ID", ""),
            "openai_roberta": os.getenv("ACADEMIC_ENGINE_FLASH_OPENAI_ROBERTA_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_OPENAI_ROBERTA_ENDPOINT_ID", ""),
            "chatgpt_roberta": os.getenv("ACADEMIC_ENGINE_FLASH_CHATGPT_ROBERTA_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_FLASH_CHATGPT_ROBERTA_ENDPOINT_ID", ""),
        }
        flash_endpoint_ids = {key: value for key, value in flash_endpoint_ids.items() if value}
        return cls(
            deepseek_api_key=api_key,
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL") or file_values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL") or file_values.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            max_refinement_cycles=max(1, min(2, cycles)),
            use_mock_provider=(use_mock_provider if use_mock_provider is not None else api_key is None),
            detector_set=configured_detector_set,
            include_hf_detector=include_hf,
            hf_detector_model=os.getenv("ACADEMIC_ENGINE_HF_DETECTOR_MODEL")
            or file_values.get("ACADEMIC_ENGINE_HF_DETECTOR_MODEL", "openai-community/roberta-base-openai-detector"),
            detector_execution_mode=execution_mode if execution_mode in {"sequential", "parallel"} else "sequential",
            detector_concurrency=max(1, min(2, concurrency)),
            candidate_generation_concurrency=max(1, min(7, candidate_generation_concurrency)),
            community_candidate_limit=max(1, min(8, community_limit)),
            binoculars_model_name=os.getenv("ACADEMIC_ENGINE_BINOCULARS_MODEL")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_MODEL", "tiiuae/falcon-7b"),
            binoculars_observer_name=os.getenv("ACADEMIC_ENGINE_BINOCULARS_OBSERVER")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_OBSERVER", "tiiuae/falcon-7b-instruct"),
            binoculars_performer_model=os.getenv("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_MODEL")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_MODEL")
            or None,
            binoculars_performer_base_url=os.getenv("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_BASE_URL")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_BASE_URL")
            or None,
            binoculars_performer_api_key=os.getenv("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_API_KEY")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_PERFORMER_API_KEY")
            or None,
            binoculars_observer_model=os.getenv("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_MODEL")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_MODEL")
            or None,
            binoculars_observer_base_url=os.getenv("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_BASE_URL")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_BASE_URL")
            or None,
            binoculars_observer_api_key=os.getenv("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_API_KEY")
            or file_values.get("ACADEMIC_ENGINE_BINOCULARS_OBSERVER_API_KEY")
            or None,
            binoculars_cli=os.getenv("ACADEMIC_ENGINE_BINOCULARS_CLI") or file_values.get("ACADEMIC_ENGINE_BINOCULARS_CLI") or None,
            ghostbuster_cli=os.getenv("ACADEMIC_ENGINE_GHOSTBUSTER_CLI") or file_values.get("ACADEMIC_ENGINE_GHOSTBUSTER_CLI") or None,
            mage_cli=os.getenv("ACADEMIC_ENGINE_MAGE_CLI") or file_values.get("ACADEMIC_ENGINE_MAGE_CLI") or None,
            radar_cli=os.getenv("ACADEMIC_ENGINE_RADAR_CLI") or file_values.get("ACADEMIC_ENGINE_RADAR_CLI") or None,
            official_binoculars_cli=os.getenv("ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI")
            or file_values.get("ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI")
            or None,
            official_ghostbuster_cli=os.getenv("ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI")
            or file_values.get("ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI")
            or None,
            official_fast_detectgpt_cli=os.getenv("ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI")
            or file_values.get("ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI")
            or None,
            official_detector_timeout_seconds=max(
                5,
                min(
                    1800,
                    int(
                        os.getenv("ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS")
                        or file_values.get("ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS", "300")
                    ),
                ),
            ),
            official_flash_endpoint_id=os.getenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID")
            or file_values.get("ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID")
            or None,
            official_flash_timeout_seconds=max(
                30,
                min(
                    1800,
                    int(
                        os.getenv("ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS")
                        or file_values.get("ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS", "900")
                    ),
                ),
            ),
            runpod_api_key=runpod_api_key,
            flash_detector_profile=flash_detector_profile,
            flash_detector_names=flash_detector_names,
            flash_mode=flash_mode,
            flash_endpoint_id=os.getenv("ACADEMIC_ENGINE_FLASH_ENDPOINT_ID") or file_values.get("ACADEMIC_ENGINE_FLASH_ENDPOINT_ID") or None,
            flash_endpoint_ids=flash_endpoint_ids,
            flash_timeout_seconds=max(
                30,
                min(
                    600,
                    int(os.getenv("ACADEMIC_ENGINE_FLASH_TIMEOUT_SECONDS") or file_values.get("ACADEMIC_ENGINE_FLASH_TIMEOUT_SECONDS", "120")),
                ),
            ),
        )
