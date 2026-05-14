"""Crafter pre-generative anchor policy for Stage H H-2."""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l3_deliberation.contracts import Candidate


class AnchorAgentState(Protocol):
    top_drive: str
    drive_levels: dict[str, float]
    signal_summary: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    compatibility_pressure_count: int
    primary_pressure_reason: str
    primary_pressure_severity: str
    seconds_to_heartbeat: float | None


OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
ESCALATE_FIRST_PROFILE = "escalate_first"
HIGH_RISK_ESCALATION_REASONS = frozenset({"health_critical", "threat_visible"})
COMPATIBILITY_RELEASE_IMPACT = {
    OBSERVE_FIRST_PROFILE: {
        "metabolic": 0.1,
        "safety": 0.1,
        "recovery": 0.0,
        "acquisition": 0.4,
        "capability": 0.3,
    },
    STABILIZE_FIRST_PROFILE: {
        "metabolic": 0.7,
        "safety": 0.8,
        "recovery": 0.6,
        "acquisition": 0.1,
        "capability": 0.0,
    },
    ESCALATE_FIRST_PROFILE: {
        "metabolic": 0.2,
        "safety": 0.9,
        "recovery": 0.1,
        "acquisition": -0.1,
        "capability": -0.1,
    },
}


def admit_crafter_candidates(
    agent_state: AnchorAgentState,
    *,
    runtime_gate_projection: dict[str, Any],
) -> list[Candidate]:
    del runtime_gate_projection
    metabolic = float(agent_state.drive_levels.get("metabolic", 0.0))
    safety = float(agent_state.drive_levels.get("safety", 0.0))
    recovery = float(agent_state.drive_levels.get("recovery", 0.0))

    if safety >= 0.7:
        profiles = [ESCALATE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE]
    elif metabolic >= 0.65 or recovery >= 0.65:
        profiles = [STABILIZE_FIRST_PROFILE]
    else:
        profiles = [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE]

    return [
        _build_candidate(agent_state, profile)
        for profile in profiles
        if _profile_admitted(profile, agent_state)
    ]


def restriction_reasons_for_crafter_candidates(
    agent_state: AnchorAgentState,
    candidates: list[Candidate],
) -> tuple[str, ...]:
    reasons = [f"admitted_candidate_schemas={len(candidates)}"]
    if float(agent_state.drive_levels.get("safety", 0.0)) >= 0.7:
        reasons.append("low_health_no_engagement")
    if float(agent_state.drive_levels.get("metabolic", 0.0)) >= 0.65:
        reasons.append("low_water_no_distant_action")
    if float(agent_state.drive_levels.get("recovery", 0.0)) >= 0.65:
        reasons.append("energy_floor_respect")
    return tuple(reasons)


def _profile_admitted(candidate_profile: str, agent_state: AnchorAgentState) -> bool:
    if candidate_profile == ESCALATE_FIRST_PROFILE:
        return agent_state.primary_pressure_reason in HIGH_RISK_ESCALATION_REASONS or float(agent_state.drive_levels.get("safety", 0.0)) >= 0.7
    return True


def _build_candidate(agent_state: AnchorAgentState, candidate_profile: str) -> Candidate:
    from eva.l3_deliberation.contracts import Candidate

    action = {
        OBSERVE_FIRST_PROFILE: "noop",
        STABILIZE_FIRST_PROFILE: "sleep",
        ESCALATE_FIRST_PROFILE: "do",
    }[candidate_profile]
    return Candidate(
        candidate_id=f"candidate-compatibility-{candidate_profile.replace('_', '-')}",
        capability="compatibility_response",
        action="compatibility_release",
        parameter_domain={
            "candidate_profile": candidate_profile,
            "preferred_action": action,
            "top_drive": agent_state.top_drive,
            "compatibility_pressure_count": agent_state.compatibility_pressure_count,
            "primary_pressure_reason": agent_state.primary_pressure_reason,
            **dict(agent_state.runtime_gate_context),
        },
        justification=(
            f"candidate_profile={candidate_profile}",
            f"top_drive={agent_state.top_drive}",
        ),
        drive_impact_schema=dict(COMPATIBILITY_RELEASE_IMPACT[candidate_profile]),
        side_effect_class="crafter_action_surface",
    )


__all__ = [
    "COMPATIBILITY_RELEASE_IMPACT",
    "ESCALATE_FIRST_PROFILE",
    "HIGH_RISK_ESCALATION_REASONS",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "admit_crafter_candidates",
    "restriction_reasons_for_crafter_candidates",
]
