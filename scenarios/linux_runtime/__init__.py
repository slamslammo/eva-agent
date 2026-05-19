"""Linux runtime scenario package for Phase A runtime activation."""

from __future__ import annotations

from dataclasses import replace

from eva.scenario_bundle import (
    ActionPolicyBundle,
    AnchorPolicyBundle,
    OutcomeObserverBundle,
    PriorSkillBundle,
    RuntimeScenarioBundle,
    SensorPolicyBundle,
    activate_runtime_scenario,
)
from eva.l2_drive.drive_registry import register_default_drive_preset
from eva.persistence_targets import build_linux_runtime_persistence_hierarchy, register_default_persistence_hierarchy

from .actions import (
    ACTION_TO_ALLOWED_STATES,
    ACTION_TO_POSTURE,
    ACTION_TO_STATE_MODE,
    ALL_LIFE_STATES,
    DEFAULT_RESPONSE_MODE,
    ESCALATE_ACTION,
    RECHECK_ACTION,
    REPAIR_ACTION,
    build_integrity_response_candidates,
    execute_linux_runtime_action,
    filter_response_candidates,
    select_integrity_response,
    select_response_action,
)
from .anchors import (
    COMPATIBILITY_RELEASE_IMPACT,
    ESCALATE_FIRST_PROFILE,
    HIGH_RISK_ESCALATION_REASONS,
    OBSERVE_FIRST_PROFILE,
    STABILIZE_FIRST_PROFILE,
    admit_linux_runtime_candidates,
    restriction_reasons_for_linux_runtime_candidates,
)
from .dimensions import LINUX_RUNTIME_DIMENSION_SPECS
from .drive_preset import DEFAULT_DRIVE_UPDATE_POLICY, DRIVE_TYPES, DRIVE_TYPE_BY_DIMENSION, LINUX_RUNTIME_DRIVE_PRESET
from .outcome_observers import build_learning_outcome_content, evaluate_response_outcome, expected_outcome_for_release
from .prior_skills import (
    build_linux_runtime_inherited_prior_registry,
    build_linux_runtime_prior_skill_registry,
    build_linux_runtime_startup_prior_registry,
    build_situation_key_from_values,
    derive_habit_skills,
    habit_skill_match_for_candidate_profile,
    situation_key_from_learning_outcome,
    summarize_habit_bias,
)
from .sensors import linux_runtime_sensor_providers

LINUX_RUNTIME_SCENARIO_BUNDLE = RuntimeScenarioBundle(
    name="linux_runtime",
    drive_preset=LINUX_RUNTIME_DRIVE_PRESET,
    sensors=SensorPolicyBundle(
        sensor_providers=linux_runtime_sensor_providers,
        dimension_specs=LINUX_RUNTIME_DIMENSION_SPECS,
        pressure_types=tuple(dict.fromkeys(spec.pressure_type for spec in LINUX_RUNTIME_DIMENSION_SPECS)),
        # Round 1.B-4: ALL Linux pressure types are imminent-threat
        # category (runtime-integrity, continuity, resource-state, anomaly-
        # accumulation are all "runtime is in trouble" signals). This
        # keeps Linux behavior bit-equivalent to the pre-1.B-4 semantic
        # where every active pressure produced class="threat" signals.
        # Crafter is different because its pressure types span both
        # imminent threats (safety) and ongoing optimization pressures
        # (metabolic / acquisition / capability / recovery).
        imminent_threat_pressure_types=tuple(
            dict.fromkeys(spec.pressure_type for spec in LINUX_RUNTIME_DIMENSION_SPECS)
        ),
    ),
    actions=ActionPolicyBundle(
        recheck_action=RECHECK_ACTION,
        repair_action=REPAIR_ACTION,
        escalate_action=ESCALATE_ACTION,
        default_response_mode=DEFAULT_RESPONSE_MODE,
        action_to_posture=ACTION_TO_POSTURE,
        action_to_state_mode=ACTION_TO_STATE_MODE,
        all_life_states=ALL_LIFE_STATES,
        action_to_allowed_states=ACTION_TO_ALLOWED_STATES,
        build_integrity_response_candidates=build_integrity_response_candidates,
        filter_response_candidates=filter_response_candidates,
        select_integrity_response=select_integrity_response,
        select_response_action=select_response_action,
        execute_response_action=execute_linux_runtime_action,
    ),
    anchors=AnchorPolicyBundle(
        observe_first_profile=OBSERVE_FIRST_PROFILE,
        stabilize_first_profile=STABILIZE_FIRST_PROFILE,
        escalate_first_profile=ESCALATE_FIRST_PROFILE,
        high_risk_escalation_reasons=HIGH_RISK_ESCALATION_REASONS,
        compatibility_release_impact=COMPATIBILITY_RELEASE_IMPACT,
        admit_candidates=admit_linux_runtime_candidates,
        restriction_reasons_for_candidates=restriction_reasons_for_linux_runtime_candidates,
    ),
    outcome_observers=OutcomeObserverBundle(
        expected_outcome_for_release=expected_outcome_for_release,
        evaluate_response_outcome=evaluate_response_outcome,
        build_learning_outcome_content=build_learning_outcome_content,
    ),
    prior_skills=PriorSkillBundle(
        habit_skill_match_for_candidate_profile=habit_skill_match_for_candidate_profile,
        build_situation_key_from_values=build_situation_key_from_values,
        derive_habit_skills=derive_habit_skills,
        situation_key_from_learning_outcome=situation_key_from_learning_outcome,
        summarize_habit_bias=summarize_habit_bias,
        build_prior_skill_registry=build_linux_runtime_prior_skill_registry,
        build_startup_prior_registry=build_linux_runtime_startup_prior_registry,
        build_inherited_prior_registry=build_linux_runtime_inherited_prior_registry,
    ),
)


def activate_linux_runtime_scenario(*, inherited_priors_path: str | None = None) -> RuntimeScenarioBundle:
    """Activate the Linux runtime bundle for framework compatibility lookups."""

    prior_skills = LINUX_RUNTIME_SCENARIO_BUNDLE.prior_skills
    if inherited_priors_path is not None:
        inherited_registry = build_linux_runtime_inherited_prior_registry(inherited_priors_path)
        prior_skills = replace(
            prior_skills,
            build_inherited_prior_registry=lambda path, registry=inherited_registry: registry,
        )
    bundle = activate_runtime_scenario(replace(LINUX_RUNTIME_SCENARIO_BUNDLE, prior_skills=prior_skills))
    register_default_drive_preset(LINUX_RUNTIME_DRIVE_PRESET)
    register_default_persistence_hierarchy(build_linux_runtime_persistence_hierarchy())
    return bundle


__all__ = [
    "ACTION_TO_ALLOWED_STATES",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "COMPATIBILITY_RELEASE_IMPACT",
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DEFAULT_RESPONSE_MODE",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
    "ESCALATE_ACTION",
    "ESCALATE_FIRST_PROFILE",
    "HIGH_RISK_ESCALATION_REASONS",
    "LINUX_RUNTIME_DRIVE_PRESET",
    "LINUX_RUNTIME_SCENARIO_BUNDLE",
    "OBSERVE_FIRST_PROFILE",
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "STABILIZE_FIRST_PROFILE",
    "activate_linux_runtime_scenario",
]
