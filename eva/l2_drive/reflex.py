"""Minimal protective L2 reflex controller that only surfaces fast-path context."""

from __future__ import annotations

from ..kernel import ActivePressureTable, RuntimeState
from ..l1_sensing.routing import RoutingDecision

__all__ = ["maybe_run_protective_reflex"]


def maybe_run_protective_reflex(
    pressure_table: ActivePressureTable,
    runtime_state: RuntimeState,
    *,
    routing_decision: RoutingDecision,
) -> dict[str, object] | None:
    """Return bounded reflex context when routing elevates the patrol to the protective lane."""

    if routing_decision.dispatch_hint != "protective_lane":
        return None
    pressure = _first_integrity_pressure(pressure_table)
    if pressure is None:
        return None
    return {
        "response_mode": "protective_reflex",
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "pressure_reason": str(pressure.evidence.get("reason") or "unknown"),
        "life_state": runtime_state.life_state,
    }


def _first_integrity_pressure(pressure_table: ActivePressureTable):
    """Return the first active integrity pressure from the current patrol result."""

    for pressure in pressure_table.pressures:
        if pressure.type == "integrity":
            return pressure
    return None
