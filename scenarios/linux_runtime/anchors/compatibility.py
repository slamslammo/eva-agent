"""Linux runtime anchor admission policy for Phase A."""

from __future__ import annotations

from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l3_deliberation.contracts import Candidate


class AnchorAgentState(Protocol):
    """Minimal projected agent state needed by the Linux runtime anchor policy."""

    top_drive: str
    signal_summary: dict[str, Any]
    compatibility_pressure_count: int
    primary_pressure_reason: str
    primary_pressure_severity: str
    seconds_to_heartbeat: float | None


OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
ESCALATE_FIRST_PROFILE = "escalate_first"
HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC = 0.75
HIGH_RISK_ESCALATION_REASONS = frozenset({
    "runtime_files_missing",
    "runtime_not_writable",
    "recent_distress_detected",
})
ESCALATE_FIRST_ADMISSION_SEVERITIES = frozenset({"critical"})
COMPATIBILITY_RELEASE_IMPACT = {
    STABILIZE_FIRST_PROFILE: {
        "survival": 0.7,
        "integrity": 0.5,
        "continuity": 0.2,
        "curiosity": -0.1,
    },
    OBSERVE_FIRST_PROFILE: {
        "survival": 0.2,
        "integrity": 0.1,
        "continuity": 0.3,
        "curiosity": 0.4,
    },
    ESCALATE_FIRST_PROFILE: {
        "survival": 0.5,
        "integrity": 0.8,
        "continuity": 0.4,
        "curiosity": -0.3,
    },
}


def admit_linux_runtime_candidates(
    agent_state: AnchorAgentState,
    *,
    runtime_gate_projection: dict[str, Any],
) -> list[Candidate]:
    """Return the base Linux runtime candidates admitted before habit shaping."""

    admitted = _build_base_candidates(
        agent_state,
        runtime_gate_projection=runtime_gate_projection,
    )
    seconds_to_heartbeat = agent_state.seconds_to_heartbeat
    if seconds_to_heartbeat is not None and seconds_to_heartbeat <= HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC:
        return [
            candidate
            for candidate in admitted
            if str(candidate.parameter_domain.get("candidate_profile") or "") == STABILIZE_FIRST_PROFILE
        ]
    return admitted


def restriction_reasons_for_linux_runtime_candidates(
    agent_state: AnchorAgentState,
    candidates: list[Candidate],
) -> tuple[str, ...]:
    """Return compact reasons that explain Linux runtime schema admission."""

    reasons: list[str] = []
    seconds_to_heartbeat = agent_state.seconds_to_heartbeat
    if seconds_to_heartbeat is not None and seconds_to_heartbeat <= HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC:
        reasons.append("heartbeat_window_narrows_to_stabilize_first")
    if not candidates:
        reasons.append("no_admitted_candidate_schemas")
        return tuple(reasons)
    reasons.insert(0, f"admitted_candidate_schemas={len(candidates)}")
    if len(candidates) == 1 and "habit_candidate_narrowing" in candidates[0].justification:
        reasons.append("habit_candidate_narrowing")
    if any(str(candidate.parameter_domain.get("candidate_profile") or "") == ESCALATE_FIRST_PROFILE for candidate in candidates):
        reasons.append("high_risk_escalation_schema_admitted")
    elif (
        agent_state.primary_pressure_reason in HIGH_RISK_ESCALATION_REASONS
        and not _can_admit_escalate_first(agent_state)
    ):
        reasons.append("high_risk_escalation_schema_blocked_by_secondary_gate")
    return tuple(reasons)


def _build_base_candidates(
    agent_state: AnchorAgentState,
    *,
    runtime_gate_projection: dict[str, Any],
) -> list[Candidate]:
    """Build the Linux runtime candidate set before schema admission narrowing."""

    common_domain = {
        "top_drive": agent_state.top_drive,
        "threat_signal_count": int(agent_state.signal_summary.get("threat_signal_count", 0)),
        "compatibility_pressure_count": agent_state.compatibility_pressure_count,
        "primary_pressure_reason": agent_state.primary_pressure_reason,
        **runtime_gate_projection,
    }
    common_justification = (
        f"top_drive={agent_state.top_drive}",
        f"threat_signal_count={int(agent_state.signal_summary.get('threat_signal_count', 0))}",
        f"primary_pressure_reason={agent_state.primary_pressure_reason}",
    )
    escalate_first_admitted = _can_admit_escalate_first(agent_state)
    return [
        _build_candidate(
            candidate_id="candidate-compatibility-observe-first",
            candidate_profile=OBSERVE_FIRST_PROFILE,
            common_domain=common_domain,
            common_justification=common_justification,
        ),
        _build_candidate(
            candidate_id="candidate-compatibility-stabilize-first",
            candidate_profile=STABILIZE_FIRST_PROFILE,
            common_domain=common_domain,
            common_justification=common_justification,
        ),
        *(
            [
                _build_candidate(
                    candidate_id="candidate-compatibility-escalate-first",
                    candidate_profile=ESCALATE_FIRST_PROFILE,
                    common_domain=common_domain,
                    common_justification=common_justification,
                )
            ]
            if escalate_first_admitted
            else []
        ),
    ]


def _can_admit_escalate_first(agent_state: AnchorAgentState) -> bool:
    """Return whether high-risk escalation passes the Linux secondary gate."""

    return (
        agent_state.primary_pressure_reason in HIGH_RISK_ESCALATION_REASONS
        and agent_state.primary_pressure_severity in ESCALATE_FIRST_ADMISSION_SEVERITIES
    )


def _build_candidate(
    *,
    candidate_id: str,
    candidate_profile: str,
    common_domain: dict[str, Any],
    common_justification: tuple[str, ...],
) -> Candidate:
    """Build one Linux runtime candidate before habit-path shaping."""

    from eva.l3_deliberation.contracts import Candidate

    return Candidate(
        candidate_id=candidate_id,
        capability="compatibility_response",
        action="compatibility_release",
        parameter_domain={
            **common_domain,
            "candidate_profile": candidate_profile,
        },
        justification=(
            f"candidate_profile={candidate_profile}",
            *common_justification,
        ),
        drive_impact_schema=dict(COMPATIBILITY_RELEASE_IMPACT.get(candidate_profile, {})),
    )


__all__ = [
    "COMPATIBILITY_RELEASE_IMPACT",
    "ESCALATE_FIRST_ADMISSION_SEVERITIES",
    "ESCALATE_FIRST_PROFILE",
    "HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC",
    "HIGH_RISK_ESCALATION_REASONS",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "admit_linux_runtime_candidates",
    "restriction_reasons_for_linux_runtime_candidates",
]
