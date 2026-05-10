"""Active runtime scenario bundle and compatibility activation seam for Phase A."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

SensorSpecBuilder = Callable[[], tuple[Any, ...]]
SensorProviderFactory = Callable[[], tuple[SensorSpecBuilder, ...]]


@dataclass(frozen=True)
class SensorPolicyBundle:
    """Scenario-owned concrete sensor provider bundle."""

    build_host_continuity_sensor_specs: SensorSpecBuilder
    build_runtime_integrity_sensor_specs: SensorSpecBuilder
    build_resource_state_sensor_specs: SensorSpecBuilder
    build_anomaly_accumulation_sensor_specs: SensorSpecBuilder
    sensor_providers: SensorProviderFactory


@dataclass(frozen=True)
class ActionPolicyBundle:
    """Scenario-owned Step 2 action policy and executor bundle."""

    recheck_action: str
    repair_action: str
    escalate_action: str
    default_response_mode: str
    action_to_posture: dict[str, str]
    action_to_state_mode: dict[str, str]
    all_life_states: tuple[str, ...]
    action_to_allowed_states: dict[str, tuple[str, ...]]
    build_integrity_response_candidates: Callable[..., list[Any]]
    filter_response_candidates: Callable[..., list[Any]]
    select_integrity_response: Callable[..., Any]
    select_response_action: Callable[..., Any]
    execute_response_action: Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class AnchorPolicyBundle:
    """Scenario-owned anchor admission and reason policy bundle."""

    observe_first_profile: str
    stabilize_first_profile: str
    escalate_first_profile: str
    high_risk_escalation_reasons: frozenset[str]
    compatibility_release_impact: dict[str, dict[str, float]]
    admit_candidates: Callable[..., list[Any]]
    restriction_reasons_for_candidates: Callable[..., tuple[str, ...]]


@dataclass(frozen=True)
class OutcomeObserverBundle:
    """Scenario-owned outcome interpretation bundle."""

    expected_outcome_for_release: Callable[[str, str | None], str]
    evaluate_response_outcome: Callable[..., tuple[str, float, str, float]]
    build_learning_outcome_content: Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class PriorSkillBundle:
    """Scenario-owned prior-skill derivation bundle."""

    habit_skill_match_for_candidate_profile: Callable[[str | None], bool]
    build_situation_key_from_values: Callable[..., str]
    derive_habit_skills: Callable[..., list[dict[str, Any]]]
    situation_key_from_learning_outcome: Callable[[dict[str, Any]], str]
    summarize_habit_bias: Callable[..., list[dict[str, Any]]]


@dataclass(frozen=True)
class RuntimeScenarioBundle:
    """Full concrete scenario assembly activated for one runtime."""

    name: str
    drive_preset: Any
    sensors: SensorPolicyBundle
    actions: ActionPolicyBundle
    anchors: AnchorPolicyBundle
    outcome_observers: OutcomeObserverBundle
    prior_skills: PriorSkillBundle


_ACTIVE_RUNTIME_SCENARIO: RuntimeScenarioBundle | None = None


def activate_runtime_scenario(bundle: RuntimeScenarioBundle) -> RuntimeScenarioBundle:
    """Activate one scenario bundle for subsequent framework compatibility lookups."""

    global _ACTIVE_RUNTIME_SCENARIO
    _ACTIVE_RUNTIME_SCENARIO = bundle
    return bundle


def get_active_runtime_scenario() -> RuntimeScenarioBundle:
    """Return the active runtime scenario, defaulting to Linux compatibility."""

    global _ACTIVE_RUNTIME_SCENARIO
    if _ACTIVE_RUNTIME_SCENARIO is None:
        from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE

        _ACTIVE_RUNTIME_SCENARIO = LINUX_RUNTIME_SCENARIO_BUNDLE
    return _ACTIVE_RUNTIME_SCENARIO


__all__ = [
    "ActionPolicyBundle",
    "AnchorPolicyBundle",
    "OutcomeObserverBundle",
    "PriorSkillBundle",
    "RuntimeScenarioBundle",
    "SensorPolicyBundle",
    "activate_runtime_scenario",
    "get_active_runtime_scenario",
]
