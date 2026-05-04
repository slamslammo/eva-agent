"""Candidate-domain restriction composed from structural and dynamic anchors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..l3_deliberation.contracts import Candidate, DeliberationInput
from .dynamic import apply_dynamic_anchor
from .structural import apply_structural_anchor

OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC = 0.75
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
}


@dataclass(frozen=True)
class AgentState:
    """Projected runtime and drive state used to admit candidate schemas."""

    top_drive: str
    drive_levels: dict[str, float]
    signal_summary: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    compatibility_pressure_count: int = 0
    seconds_to_heartbeat: float | None = None
    working_memory_context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the projected anchor-time agent state."""

        payload = {
            "top_drive": self.top_drive,
            "drive_levels": dict(self.drive_levels),
            "signal_summary": dict(self.signal_summary),
            "runtime_gate_context": dict(self.runtime_gate_context),
            "compatibility_pressure_count": self.compatibility_pressure_count,
        }
        if self.seconds_to_heartbeat is not None:
            payload["seconds_to_heartbeat"] = self.seconds_to_heartbeat
        if self.working_memory_context is not None:
            payload["working_memory_context"] = dict(self.working_memory_context)
        return payload


@dataclass(frozen=True)
class CandidateSchema:
    """An admitted candidate schema before concrete candidate materialization."""

    candidate_id: str
    candidate_profile: str
    capability: str = "compatibility_response"
    action: str = "compatibility_release"
    parameter_domain: dict[str, Any] = field(default_factory=dict)
    justification: tuple[str, ...] = ()
    drive_impact_schema: dict[str, float] = field(default_factory=dict)
    side_effect_class: str = "compatibility_side_effect"

    def to_candidate(self) -> Candidate:
        """Materialize the concrete candidate for the reasoning layer."""

        return Candidate(
            candidate_id=self.candidate_id,
            capability=self.capability,
            action=self.action,
            parameter_domain=dict(self.parameter_domain),
            justification=self.justification,
            drive_impact_schema=dict(self.drive_impact_schema),
            side_effect_class=self.side_effect_class,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the admitted candidate schema."""

        payload = {
            "candidate_id": self.candidate_id,
            "candidate_profile": self.candidate_profile,
            "capability": self.capability,
            "action": self.action,
            "parameter_domain": dict(self.parameter_domain),
            "justification": list(self.justification),
            "drive_impact_schema": dict(self.drive_impact_schema),
            "side_effect_class": self.side_effect_class,
        }
        return payload


@dataclass(frozen=True)
class ActionDomain:
    """Pre-generative domain of admitted candidate schemas."""

    agent_state: AgentState
    admitted_candidate_schemas: tuple[CandidateSchema, ...] = ()
    restriction_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pre-generative action domain."""

        return {
            "agent_state": self.agent_state.to_dict(),
            "admitted_candidate_schemas": [schema.to_dict() for schema in self.admitted_candidate_schemas],
            "restriction_reasons": list(self.restriction_reasons),
        }


def build_action_domain(deliberation_input: DeliberationInput) -> ActionDomain:
    """Build the pre-generative anchor domain for candidate materialization."""

    signal_summary = deliberation_input.signal_batch.get("summary", {})
    top_drive = str(deliberation_input.drive_broadcast.get("top_drive") or "unknown")
    drive_levels = deliberation_input.drive_broadcast.get("drive_levels")
    normalized_drive_levels = dict(drive_levels) if isinstance(drive_levels, dict) else {}
    compatibility_pressure_count = 0
    if deliberation_input.compatibility_pressure_table is not None:
        pressures = deliberation_input.compatibility_pressure_table.get("pressures", [])
        if isinstance(pressures, list):
            compatibility_pressure_count = len(pressures)
    runtime_gate = deliberation_input.runtime_gate_context
    agent_state = AgentState(
        top_drive=top_drive,
        drive_levels=normalized_drive_levels,
        signal_summary=dict(signal_summary),
        runtime_gate_context=dict(runtime_gate),
        compatibility_pressure_count=compatibility_pressure_count,
        seconds_to_heartbeat=_seconds_to_heartbeat(runtime_gate),
        working_memory_context=deliberation_input.working_memory_context,
    )

    admitted_candidates = _admit_base_candidates(agent_state)
    from ..l3_deliberation.peer_circuit.habit_track import shape_candidates_with_habit_track

    admitted_candidates = shape_candidates_with_habit_track(admitted_candidates, deliberation_input)
    return ActionDomain(
        agent_state=agent_state,
        admitted_candidate_schemas=tuple(_schema_from_candidate(candidate) for candidate in admitted_candidates),
        restriction_reasons=_restriction_reasons_from_candidates(agent_state, admitted_candidates),
    )


def restrict_candidate_domain(candidate: Candidate, deliberation_input: DeliberationInput) -> Candidate:
    """Restrict one candidate domain through the current anchor stack."""

    anchored = apply_structural_anchor(candidate, deliberation_input)
    return apply_dynamic_anchor(anchored, deliberation_input)


def _admit_base_candidates(agent_state: AgentState) -> list[Candidate]:
    """Return the base candidate set admitted before concrete materialization."""

    admitted = _build_base_candidates(agent_state)
    seconds_to_heartbeat = agent_state.seconds_to_heartbeat
    if seconds_to_heartbeat is not None and seconds_to_heartbeat <= HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC:
        return [
            candidate
            for candidate in admitted
            if str(candidate.parameter_domain.get("candidate_profile") or "") == STABILIZE_FIRST_PROFILE
        ]
    return admitted


def _build_base_candidates(agent_state: AgentState) -> list[Candidate]:
    """Build the temporary candidate set before schema admission."""

    common_domain = {
        "top_drive": agent_state.top_drive,
        "threat_signal_count": int(agent_state.signal_summary.get("threat_signal_count", 0)),
        "compatibility_pressure_count": agent_state.compatibility_pressure_count,
    }
    common_justification = (
        f"top_drive={agent_state.top_drive}",
        f"threat_signal_count={int(agent_state.signal_summary.get('threat_signal_count', 0))}",
    )
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
    ]


def _build_candidate(
    *,
    candidate_id: str,
    candidate_profile: str,
    common_domain: dict[str, Any],
    common_justification: tuple[str, ...],
) -> Candidate:
    """Build one base candidate before habit-path shaping."""

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


def _schema_from_candidate(candidate: Candidate) -> CandidateSchema:
    """Project one temporary candidate into an admitted schema."""

    return CandidateSchema(
        candidate_id=candidate.candidate_id,
        candidate_profile=str(candidate.parameter_domain.get("candidate_profile") or "unknown"),
        capability=candidate.capability,
        action=candidate.action,
        parameter_domain=dict(candidate.parameter_domain),
        justification=tuple(candidate.justification),
        drive_impact_schema=dict(candidate.drive_impact_schema),
        side_effect_class=candidate.side_effect_class,
    )


def _restriction_reasons_from_candidates(agent_state: AgentState, candidates: list[Candidate]) -> tuple[str, ...]:
    """Return compact reasons that explain which schemas were admitted."""

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
    return tuple(reasons)


def _seconds_to_heartbeat(runtime_gate_context: dict[str, Any]) -> float | None:
    """Return the remaining heartbeat lead time if it was projected by the kernel."""

    value = runtime_gate_context.get("seconds_to_heartbeat")
    if value is None:
        return None
    return float(value)


__all__ = [
    "ActionDomain",
    "AgentState",
    "CandidateSchema",
    "COMPATIBILITY_RELEASE_IMPACT",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "build_action_domain",
    "apply_dynamic_anchor",
    "apply_structural_anchor",
    "restrict_candidate_domain",
]
