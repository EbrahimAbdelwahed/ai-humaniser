from __future__ import annotations

from dataclasses import dataclass


ROBERTA_CLUSTER_MEMBERS = ("radar", "openai_roberta", "chatgpt_roberta")


@dataclass(frozen=True)
class DetectorProfile:
    name: str
    family: str
    profile: str
    model_name: str
    implementation_kind: str
    expected_device: str
    cost_class: str
    cluster: str | None
    default_weight: float
    known_status: str


DETECTOR_REGISTRY: dict[str, DetectorProfile] = {
    "radar": DetectorProfile(
        name="radar",
        family="roberta_sequence_classifier",
        profile="stable",
        model_name="Shushant/adal-roberta-detector",
        implementation_kind="hf_sequence_classification",
        expected_device="gpu_optional",
        cost_class="low_gpu",
        cluster="roberta_cluster",
        default_weight=0.24,
        known_status="stable_cluster_member",
    ),
    "openai_roberta": DetectorProfile(
        name="openai_roberta",
        family="roberta_sequence_classifier",
        profile="stable",
        model_name="openai-community/roberta-base-openai-detector",
        implementation_kind="hf_sequence_classification",
        expected_device="gpu_optional",
        cost_class="low_gpu",
        cluster="roberta_cluster",
        default_weight=0.24,
        known_status="stable_cluster_member",
    ),
    "chatgpt_roberta": DetectorProfile(
        name="chatgpt_roberta",
        family="roberta_sequence_classifier",
        profile="stable",
        model_name="Hello-SimpleAI/chatgpt-detector-roberta",
        implementation_kind="hf_sequence_classification",
        expected_device="gpu_optional",
        cost_class="low_gpu",
        cluster="roberta_cluster",
        default_weight=0.24,
        known_status="stable_cluster_member",
    ),
    "binoculars": DetectorProfile(
        name="binoculars",
        family="cross_perplexity",
        profile="calibration",
        model_name="api_configured_observer_performer",
        implementation_kind="api_logprobs_cross_perplexity",
        expected_device="external_api_optional",
        cost_class="api_configured",
        cluster=None,
        default_weight=0.55,
        known_status="calibration_interface_only",
    ),
    "ghostbuster": DetectorProfile(
        name="ghostbuster",
        family="feature_detector",
        profile="experimental",
        model_name="official_runtime_required",
        implementation_kind="feature_proxy",
        expected_device="cpu_or_gpu_optional",
        cost_class="experimental",
        cluster=None,
        default_weight=0.32,
        known_status="proxy_not_stable",
    ),
    "mage": DetectorProfile(
        name="mage",
        family="sequence_classifier",
        profile="experimental",
        model_name="yaful/MAGE",
        implementation_kind="hf_sequence_classification",
        expected_device="gpu_optional",
        cost_class="experimental",
        cluster=None,
        default_weight=0.32,
        known_status="experimental",
    ),
}


DETECTOR_PROFILES: dict[str, tuple[str, ...]] = {
    "stable": ("roberta_cluster",),
    "model": ("roberta_cluster",),
    "calibration": ("roberta_cluster", "binoculars"),
    "experimental": ("roberta_cluster", "binoculars", "ghostbuster"),
    "all": ("roberta_cluster", "binoculars", "ghostbuster", "mage"),
}


def expand_profile(profile: str) -> tuple[str, ...]:
    return DETECTOR_PROFILES.get(profile, DETECTOR_PROFILES["stable"])


def expand_runtime_detectors(names: tuple[str, ...]) -> tuple[str, ...]:
    expanded: list[str] = []
    for name in names:
        if name == "roberta_cluster":
            expanded.extend(ROBERTA_CLUSTER_MEMBERS)
        else:
            expanded.append(name)
    return tuple(dict.fromkeys(expanded))


def registry_inventory() -> dict[str, object]:
    return {
        "clusters": {
            "roberta_cluster": {
                "members": list(ROBERTA_CLUSTER_MEMBERS),
                "role": "correlated supervised baseline",
                "weighting": "consumed as one clustered signal",
            }
        },
        "profiles": {key: list(value) for key, value in DETECTOR_PROFILES.items()},
        "detectors": {name: profile.__dict__ for name, profile in DETECTOR_REGISTRY.items()},
    }
