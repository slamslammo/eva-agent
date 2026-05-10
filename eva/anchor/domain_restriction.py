"""Candidate-domain restriction composed from structural and dynamic anchors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scenarios.linux_runtime.anchors import (
    COMPATIBILITY_RELEASE_IMPACT as _COMPATIBILITY_RELEASE_IMPACT,
    ESCALATE_FIRST_PROFILE as _ESCALATE_FIRST_PROFILE,
    HIGH_RISK_ESCALATION_REASONS as _HIGH_RISK_ESCALATION_REASONS,
    OBSERVE_FIRST_PROFILE as _OBSERVE_FIRST_PROFILE,
    STABILIZE_FIRST_PROFILE as _STABILIZE_FIRST_PROFILE,
    admit_linux_runtime_candidates,
    restriction_reasons_for_linux_runtime_candidates,
)

from ..l3_deliberation.contracts import Candidate, DeliberationInput
from .dynamic import apply_dynamic_anchor
from .structural import apply_structural_anchor

OBSERVE_FIRST_PROFILE = _OBSERVE_FIRST_PROFILE
STABILIZE_FIRST_PROFILE = _STABILIZE_FIRST_PROFILE
ESCALATE_FIRST_PROFILE = _ESCALATE_FIRST_PROFILE
HIGH_RISK_ESCALATION_REASONS = _HIGH_RISK_ESCALATION_REASONS
COMPATIBILITY_RELEASE_IMPACT = _COMPATIBILITY_RELEASE_IMPACT


@dataclass(frozen=True)
class AgentState:
    """Projected runtime and drive state used to admit candidate schemas."""

    top_drive: str
    drive_levels: dict[str, float]
    signal_summary: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    compatibility_pressure_count: int = 0
    primary_pressure_reason: str = "none"
    primary_pressure_severity: str = "healthy"
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
            "primary_pressure_reason": self.primary_pressure_reason,
            "primary_pressure_severity": self.primary_pressure_severity,
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
    primary_pressure_reason = "none"
    primary_pressure_severity = "healthy"
    if deliberation_input.compatibility_pressure_table is not None:
        pressures = deliberation_input.compatibility_pressure_table.get("pressures", [])
        if isinstance(pressures, list):
            compatibility_pressure_count = len(pressures)
            first_integrity_pressure = next(
                (
                    pressure
                    for pressure in pressures
                    if isinstance(pressure, dict) and str(pressure.get("type") or "") == "integrity"
                ),
                None,
            )
            if first_integrity_pressure is not None:
                primary_pressure_severity = str(first_integrity_pressure.get("severity") or "healthy")
                evidence = first_integrity_pressure.get("evidence")
                if isinstance(evidence, dict):
                    primary_pressure_reason = str(evidence.get("reason") or "none")
    runtime_gate = deliberation_input.runtime_gate_context
    agent_state = AgentState(
        top_drive=top_drive,
        drive_levels=normalized_drive_levels,
        signal_summary=dict(signal_summary),
        runtime_gate_context=dict(runtime_gate),
        compatibility_pressure_count=compatibility_pressure_count,
        primary_pressure_reason=primary_pressure_reason,
        primary_pressure_severity=primary_pressure_severity,
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


def apply_structural_anchors(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[Candidate]:
    """Project runtime-gate fields onto compatibility or manually built candidates."""

    return [restrict_candidate_domain(candidate, deliberation_input) for candidate in candidates]


def _admit_base_candidates(agent_state: AgentState) -> list[Candidate]:
    """Return the base candidate set admitted before concrete materialization."""

    return admit_linux_runtime_candidates(
        agent_state,
        runtime_gate_projection=_runtime_gate_projection(agent_state),
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

    return restriction_reasons_for_linux_runtime_candidates(agent_state, candidates)


def _runtime_gate_projection(agent_state: AgentState) -> dict[str, Any]:
    """Return the minimal runtime-gate projection that must already exist pre-generation."""

    runtime_gate = agent_state.runtime_gate_context
    return {
        "instance_valid": bool(runtime_gate.get("instance_valid", False)),
        "turn_allowed": bool(runtime_gate.get("turn_allowed", False)),
        "critical_blocked": bool(runtime_gate.get("critical_blocked", False)),
        "conservative_mode": bool(runtime_gate.get("conservative_mode", False)),
        "life_state": runtime_gate.get("life_state"),
    }


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
    "ESCALATE_FIRST_PROFILE",
    "HIGH_RISK_ESCALATION_REASONS",
    "build_action_domain",
    "apply_dynamic_anchor",
    "apply_structural_anchor",
    "apply_structural_anchors",
    "restrict_candidate_domain",
]
