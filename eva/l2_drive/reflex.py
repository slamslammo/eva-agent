"""Bounded L2 reflex helpers for the threat-triggered fast path."""

from __future__ import annotations

from ..kernel import ActivePressure, ActivePressureTable, RuntimeState
from ..l1_sensing.routing import RoutingDecision
from ..l3_deliberation.peer_circuit.mediator import mint_reflex_release

__all__ = ["build_protective_reflex"]


def build_protective_reflex(
    pressure_table: ActivePressureTable,
    runtime_state: RuntimeState,
    *,
    routing_decision: RoutingDecision,
) -> dict[str, object] | None:
    """Return a bounded mediated reflex plan when routing elevates the patrol to the protective lane."""

    if routing_decision.dispatch_hint != "protective_lane" or routing_decision.deliberation_allowed:
        return None
    pressure = _first_integrity_pressure(pressure_table)
    if pressure is None:
        return None
    release_decision = mint_reflex_release(
        candidate_profile=_candidate_profile_for_pressure(pressure),
        rationale=("threat_signal_fast_path", f"pressure_reason={_pressure_reason(pressure)}"),
    )
    return {
        "response_mode": "protective_reflex",
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "pressure_reason": _pressure_reason(pressure),
        "life_state": runtime_state.life_state,
        "release_decision": release_decision,
        "pressure": pressure,
    }


def _candidate_profile_for_pressure(pressure: ActivePressure) -> str:
    """Map one integrity pressure into the bounded reflex candidate profile."""

    reason = _pressure_reason(pressure)
    if reason in {"runtime_files_missing", "runtime_not_writable", "recent_distress_detected"}:
        return "escalate_first"
    if reason == "instance_invalid":
        return "observe_first"
    return "stabilize_first"


def _pressure_reason(pressure: ActivePressure) -> str:
    """Return the compact reason string from one active pressure."""

    return str(pressure.evidence.get("reason") or "unknown")


def _first_integrity_pressure(pressure_table: ActivePressureTable) -> ActivePressure | None:
    """Return the first active integrity pressure from the current patrol result."""

    for pressure in pressure_table.pressures:
        if pressure.type == "integrity":
            return pressure
    return None
