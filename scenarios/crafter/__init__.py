"""Crafter scenario activation surface for Stage H H-2."""

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
from eva.persistence_targets import register_default_persistence_hierarchy

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
    execute_crafter_action,
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
    admit_crafter_candidates,
    restriction_reasons_for_crafter_candidates,
)
from .dimensions import CRAFTER_DIMENSION_SPECS
from .drive_preset import CRAFTER_DRIVE_PRESET
from .outcome_observers import build_learning_outcome_content, evaluate_response_outcome, expected_outcome_for_release
from .persistence import build_crafter_persistence_hierarchy
from .prior_skills import (
    build_crafter_inherited_prior_registry,
    build_situation_key_from_values,
    derive_habit_skills,
    habit_skill_match_for_candidate_profile,
    situation_key_from_learning_outcome,
    summarize_habit_bias,
)
from .prior_skills.bundle import build_crafter_prior_skill_registry, build_crafter_startup_prior_registry
from .sensors import crafter_sensor_providers

CRAFTER_SCENARIO_BUNDLE = RuntimeScenarioBundle(
    name="crafter",
    drive_preset=CRAFTER_DRIVE_PRESET,
    sensors=SensorPolicyBundle(
        sensor_providers=crafter_sensor_providers,
        dimension_specs=CRAFTER_DIMENSION_SPECS,
        pressure_types=tuple(dict.fromkeys(spec.pressure_type for spec in CRAFTER_DIMENSION_SPECS)),
        # Round 1.B-4: only ``safety`` pressures (zombies, threats in
        # local_view) qualify as imminent threats in Crafter. The other
        # pressure types (metabolic, recovery, acquisition, capability)
        # are ongoing pressures that influence drive levels and candidate
        # scoring but do not trigger threat-response semantics in routing
        # / curiosity suppression / memory salience. Without this
        # narrowing, an avatar with persistent food/water/energy drift
        # would have every tick classed as a threat tick, pinning
        # exploration drive at 0 and over-amplifying memory salience.
        imminent_threat_pressure_types=("safety",),
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
        execute_response_action=execute_crafter_action,
    ),
    anchors=AnchorPolicyBundle(
        observe_first_profile=OBSERVE_FIRST_PROFILE,
        stabilize_first_profile=STABILIZE_FIRST_PROFILE,
        escalate_first_profile=ESCALATE_FIRST_PROFILE,
        high_risk_escalation_reasons=HIGH_RISK_ESCALATION_REASONS,
        compatibility_release_impact=COMPATIBILITY_RELEASE_IMPACT,
        admit_candidates=admit_crafter_candidates,
        restriction_reasons_for_candidates=restriction_reasons_for_crafter_candidates,
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
        build_prior_skill_registry=build_crafter_prior_skill_registry,
        build_startup_prior_registry=build_crafter_startup_prior_registry,
        build_inherited_prior_registry=build_crafter_inherited_prior_registry,
    ),
)


def activate_crafter_scenario(*, inherited_priors_path: str | None = None) -> RuntimeScenarioBundle:
    """Activate the Crafter scenario bundle on top of the stable framework seam."""

    prior_skills = CRAFTER_SCENARIO_BUNDLE.prior_skills
    if inherited_priors_path is not None:
        inherited_registry = build_crafter_inherited_prior_registry(inherited_priors_path)
        prior_skills = replace(
            prior_skills,
            build_inherited_prior_registry=lambda path, registry=inherited_registry: registry,
        )
    activated = activate_runtime_scenario(replace(CRAFTER_SCENARIO_BUNDLE, prior_skills=prior_skills))
    register_default_drive_preset(CRAFTER_DRIVE_PRESET)
    register_default_persistence_hierarchy(build_crafter_persistence_hierarchy())
    return activated


__all__ = ["CRAFTER_SCENARIO_BUNDLE", "activate_crafter_scenario"]
