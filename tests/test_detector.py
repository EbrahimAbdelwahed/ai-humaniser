from academic_engine.config import EngineConfig
from academic_engine.detectors import (
    ApiBinocularsDetectorProvider,
    BinocularsDetectorProvider,
    CliCommunityDetectorProvider,
    FlashDetectorProvider,
    HeuristicDetectorProvider,
    HuggingFaceOpenAIDetectorProvider,
    OfficialDetectorProvider,
    detector_providers_from_config,
    official_detector_providers,
)
from academic_engine.detector_registry import expand_profile, expand_runtime_detectors


def test_detector_heuristic_flags_generic_repetition_higher():
    provider = HeuristicDetectorProvider()
    generic = "In conclusion, it is important to note that the issue is important. " * 8
    varied = "Smith (2021) reports a measured policy change. The finding is limited, but it clarifies local participation."

    assert provider.analyze(generic).score > provider.analyze(varied).score


def test_default_detector_ensemble_produces_multiple_available_signals():
    providers = detector_providers_from_config(EngineConfig.from_env(use_mock_provider=True))
    text = "Smith (2021) reports a measured policy change. The finding is limited, but it clarifies local participation."

    results = [provider.analyze(text) for provider in providers]

    assert len([result for result in results if result.available]) >= 3
    assert {result.provider_name for result in results} >= {
        "local_stylometry_burstiness",
        "local_lexical_diversity",
        "local_gltr_lite_probability_shape",
    }
    assert all(0.0 <= result.score <= 1.0 for result in results)


def test_optional_hf_detector_unavailable_does_not_break():
    result = HuggingFaceOpenAIDetectorProvider("definitely-missing-local-model").analyze("Smith (2021) found a 12% change.")

    assert result.available is False
    assert result.label == "unavailable"
    assert result.error


def test_detector_set_hf_uses_only_optional_hf_provider():
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="hf")

    providers = detector_providers_from_config(config)

    assert [provider.provider_name for provider in providers] == ["hf_roberta_base_openai_detector"]


def test_detector_set_local_plus_hf_includes_local_and_hf_providers():
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="local+hf")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert "local_stylometry_burstiness" in names
    assert names[-1] == "hf_roberta_base_openai_detector"


def test_detector_set_community_uses_community_providers_only():
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="community")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert names == ["community_binoculars", "community_ghostbuster", "community_mage", "community_radar"]


def test_detector_set_local_plus_community_includes_local_and_community():
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="local+community")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert "local_stylometry_burstiness" in names
    assert "community_binoculars" in names
    assert "hf_roberta_base_openai_detector" not in names


def test_detector_set_official_uses_official_providers_only(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="official", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert names == ["official_binoculars", "official_ghostbuster", "official_fast_detectgpt"]


def test_detector_set_official_binoculars_uses_only_official_binoculars(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="official-binoculars", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)

    assert [provider.provider_name for provider in providers] == ["official_binoculars"]


def test_detector_set_official_fast_detectgpt_uses_only_official_fast_detectgpt(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="official-fast-detectgpt", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)

    assert [provider.provider_name for provider in providers] == ["official_fast_detectgpt"]


def test_detector_set_local_plus_official_includes_local_and_official(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="local+official", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert "local_stylometry_burstiness" in names
    assert "official_binoculars" in names
    assert "community_binoculars" not in names
    assert "flash_roberta_cluster" not in names


def test_detector_set_all_includes_local_community_and_hf():
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="all")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert "local_stylometry_burstiness" in names
    assert "community_radar" in names
    assert "official_fast_detectgpt" in names
    assert names[-1] == "hf_roberta_base_openai_detector"


def test_detector_set_flash_uses_flash_providers_only(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="flash", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert names == ["flash_roberta_cluster"]


def test_flash_experimental_profile_includes_proxy_detector(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="flash", env_file=tmp_path / "missing.env")
    from dataclasses import replace

    config = replace(
        config,
        flash_detector_profile="experimental",
        flash_detector_names=("radar", "openai_roberta", "chatgpt_roberta", "binoculars", "ghostbuster"),
    )

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert names == [
        "flash_radar",
        "flash_openai_roberta",
        "flash_chatgpt_roberta",
        "flash_binoculars",
        "flash_ghostbuster",
    ]


def test_detector_set_local_plus_flash_includes_local_and_flash(tmp_path):
    config = EngineConfig.from_env(use_mock_provider=True, detector_set="local+flash", env_file=tmp_path / "missing.env")

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert "local_stylometry_burstiness" in names
    assert "flash_roberta_cluster" in names
    assert "flash_binoculars" not in names
    assert "community_binoculars" not in names


def test_flash_calibration_profile_does_not_route_binoculars_through_runpod_batch(tmp_path):
    from dataclasses import replace

    config = EngineConfig.from_env(use_mock_provider=True, detector_set="flash", env_file=tmp_path / "missing.env")
    config = replace(config, flash_detector_profile="calibration", flash_detector_names=("roberta_cluster", "binoculars"))

    providers = detector_providers_from_config(config)
    names = [provider.provider_name for provider in providers]

    assert names == ["flash_roberta_cluster"]


def test_registry_stable_profile_emits_cluster_not_independent_weights():
    assert expand_profile("stable") == ("roberta_cluster",)
    assert expand_runtime_detectors(expand_profile("stable")) == ("radar", "openai_roberta", "chatgpt_roberta")


class FakeLogprobClient:
    def logprobs(self, *, model, **kwargs):
        if model == "observer":
            return {"token_logprobs": [-1.2, -1.0]}
        return {"token_logprobs": [-1.0, -1.0]}


def test_api_binoculars_uses_fake_logprob_client():
    provider = ApiBinocularsDetectorProvider(
        observer_model="observer",
        observer_base_url="https://observer.invalid",
        observer_api_key="observer-key",
        performer_model="performer",
        performer_base_url="https://performer.invalid",
        performer_api_key="performer-key",
        client=FakeLogprobClient(),
    )

    result = provider.analyze("Smith (2021) found a 12% change.")

    assert result.available is True
    assert result.raw_result["implementation"] == "api_cross_perplexity_logprobs"
    assert 0.0 <= result.score <= 1.0


def test_api_binoculars_unavailable_without_logprobs():
    class MissingLogprobsClient:
        def logprobs(self, **kwargs):
            return {"choices": [{"logprobs": {}}]}

    provider = ApiBinocularsDetectorProvider(
        observer_model="observer",
        observer_base_url="https://observer.invalid",
        observer_api_key="observer-key",
        performer_model="performer",
        performer_base_url="https://performer.invalid",
        performer_api_key="performer-key",
        client=MissingLogprobsClient(),
    )

    result = provider.analyze("Smith (2021) found a 12% change.")

    assert result.available is False
    assert "logprobs" in result.error


def test_flash_detector_unavailable_without_config():
    result = FlashDetectorProvider(detector_name="binoculars", api_key=None, endpoint_id=None).analyze("Smith (2021) found a 12% change.")

    assert result.available is False
    assert result.provider_name == "flash_binoculars"
    assert result.provider_kind == "api"
    assert "RUNPOD_API_KEY" in result.error


def test_flash_config_parses_env_file(tmp_path, monkeypatch):
    for name in [
        "RUNPOD_API_KEY",
        "ACADEMIC_ENGINE_FLASH_DETECTORS",
        "ACADEMIC_ENGINE_FLASH_MODE",
        "ACADEMIC_ENGINE_FLASH_BINOCULARS_ENDPOINT_ID",
        "ACADEMIC_ENGINE_FLASH_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / "engine.env"
    env_file.write_text(
        "\n".join(
            [
                "RUNPOD_API_KEY=test-key",
                "ACADEMIC_ENGINE_FLASH_PROFILE=all",
                "ACADEMIC_ENGINE_FLASH_DETECTORS=binoculars,radar",
                "ACADEMIC_ENGINE_FLASH_MODE=research",
                "ACADEMIC_ENGINE_FLASH_BINOCULARS_ENDPOINT_ID=endpoint-binoculars",
                "ACADEMIC_ENGINE_FLASH_TIMEOUT_SECONDS=240",
            ]
        ),
        encoding="utf-8",
    )

    config = EngineConfig.from_env(use_mock_provider=True, detector_set="flash", env_file=env_file)

    assert config.runpod_api_key == "test-key"
    assert config.flash_detector_profile == "all"
    assert config.flash_detector_names == ("binoculars", "radar")
    assert config.flash_mode == "research"
    assert config.flash_endpoint_ids == {"binoculars": "endpoint-binoculars"}
    assert config.flash_timeout_seconds == 240


def test_official_config_parses_env_file(tmp_path, monkeypatch):
    for name in [
        "ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS",
        "ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID",
        "ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / "engine.env"
    env_file.write_text(
        "\n".join(
            [
                "ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI=/opt/binoculars-wrapper",
                "ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI=/opt/ghostbuster-wrapper",
                "ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI=/opt/fast-detectgpt-wrapper",
                "ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS=45",
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=official-endpoint",
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS=1200",
            ]
        ),
        encoding="utf-8",
    )

    config = EngineConfig.from_env(use_mock_provider=True, detector_set="official", env_file=env_file)

    assert config.official_binoculars_cli == "/opt/binoculars-wrapper"
    assert config.official_ghostbuster_cli == "/opt/ghostbuster-wrapper"
    assert config.official_fast_detectgpt_cli == "/opt/fast-detectgpt-wrapper"
    assert config.official_detector_timeout_seconds == 45
    assert config.official_flash_endpoint_id == "official-endpoint"
    assert config.official_flash_timeout_seconds == 1200


def test_official_flash_endpoint_id_autowires_binoculars_and_fast_detectgpt(tmp_path, monkeypatch):
    for name in [
        "ACADEMIC_ENGINE_OFFICIAL_BINOCULARS_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_GHOSTBUSTER_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_FAST_DETECTGPT_CLI",
        "ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID",
        "ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS",
    ]:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / "engine.env"
    env_file.write_text(
        "\n".join(
            [
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=endpoint-official",
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS=777",
            ]
        ),
        encoding="utf-8",
    )

    config = EngineConfig.from_env(use_mock_provider=True, detector_set="official", env_file=env_file)
    providers = {provider.provider_name: provider for provider in official_detector_providers(config)}

    assert "runpod_official_cli.py" in providers["official_binoculars"].cli
    assert "--endpoint-id endpoint-official" in providers["official_binoculars"].cli
    assert "--detector official_binoculars" in providers["official_binoculars"].cli
    assert "--timeout 777" in providers["official_binoculars"].cli
    assert "runpod_official_cli.py" in providers["official_fast_detectgpt"].cli
    assert "--detector official_fast_detectgpt" in providers["official_fast_detectgpt"].cli
    assert providers["official_ghostbuster"].cli is None


def test_official_flash_endpoint_timeout_controls_local_wrapper_timeout(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_ENDPOINT_ID=endpoint-official",
                "ACADEMIC_ENGINE_OFFICIAL_FLASH_TIMEOUT_SECONDS=1200",
                "ACADEMIC_ENGINE_OFFICIAL_DETECTOR_TIMEOUT_SECONDS=300",
            ]
        ),
        encoding="utf-8",
    )

    config = EngineConfig.from_env(env_file=env_file)
    providers = {provider.provider_name: provider for provider in official_detector_providers(config)}

    assert providers["official_binoculars"].timeout_seconds == 1200
    assert providers["official_fast_detectgpt"].timeout_seconds == 1200


def test_official_detectors_unavailable_without_config():
    text = "Smith (2021) found a 12% change."
    providers = [
        OfficialDetectorProvider(
            provider_name="official_binoculars",
            cli=None,
            install_hint="install binoculars",
        ),
        OfficialDetectorProvider(
            provider_name="official_ghostbuster",
            cli=None,
            install_hint="install ghostbuster",
        ),
        OfficialDetectorProvider(
            provider_name="official_fast_detectgpt",
            cli=None,
            install_hint="install fast-detectgpt",
        ),
    ]

    results = [provider.analyze(text) for provider in providers]

    assert all(result.available is False for result in results)
    assert [result.provider_name for result in results] == ["official_binoculars", "official_ghostbuster", "official_fast_detectgpt"]
    assert all(result.provider_kind == "local_model" for result in results)
    assert all("No official local CLI command" in (result.error or "") for result in results)


def test_official_cli_provider_preserves_structured_unavailable_payload(tmp_path):
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text(
        "\n".join(
            [
                "import json",
                "print(json.dumps({'available': False, 'score': 0.0, 'failure_mode': 'endpoint_error', 'error': 'endpoint missing'}))",
                "raise SystemExit(4)",
            ]
        ),
        encoding="utf-8",
    )
    provider = OfficialDetectorProvider(provider_name="official_binoculars", cli=f"python {wrapper}", install_hint="install")

    result = provider.analyze("Smith (2021) found a 12% change.")

    assert result.available is False
    assert result.error == "endpoint missing"
    assert result.raw_result["failure_mode"] == "endpoint_error"
    assert "command" in result.raw_result


def test_community_detectors_unavailable_do_not_break():
    text = "Smith (2021) found a 12% change."
    providers = [
        BinocularsDetectorProvider(model_name="missing", observer_name="missing"),
        CliCommunityDetectorProvider(provider_name="community_ghostbuster", cli=None, install_hint="install ghostbuster"),
        CliCommunityDetectorProvider(provider_name="community_mage", cli=None, install_hint="install mage"),
        CliCommunityDetectorProvider(provider_name="community_radar", cli=None, install_hint="install radar"),
    ]

    results = [provider.analyze(text) for provider in providers]

    assert all(result.available is False for result in results)
    assert all(result.provider_kind == "local_model" for result in results)
    assert all(result.error for result in results)
