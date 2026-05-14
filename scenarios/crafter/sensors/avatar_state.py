"""Crafter avatar-state sensor specs for Stage H H-1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec


def _status_for_level(value: float | None, *, critical_at: float, degraded_at: float) -> str:
    if value is None:
        return "healthy"
    if value <= critical_at:
        return "critical"
    if value <= degraded_at:
        return "degraded"
    return "healthy"


def _avatar_life_payload(context: SensingContext) -> tuple[dict[str, float | None], int]:
    observation = context.shared_facts.get("agent_observation") or {}
    visible = observation.get("visible", {}) if isinstance(observation, dict) else {}
    life_panel = visible.get("life_panel", {}) if isinstance(visible, dict) else {}
    values = life_panel.get("values", {}) if isinstance(life_panel, dict) else {}
    nearby_objects = visible.get("nearby_objects", []) if isinstance(visible, dict) else []
    payload = {
        "health": _coerce_float(values.get("health")),
        "food": _coerce_float(values.get("food")),
        "water": _coerce_float(values.get("water")),
        "energy": _coerce_float(values.get("energy")),
    }
    threat_count = len(nearby_objects) if isinstance(nearby_objects, list) else 0
    return payload, threat_count


def _avatar_metabolic_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, _ = _avatar_life_payload(context)
    food_status = _status_for_level(payload["food"], critical_at=3.0, degraded_at=6.0)
    water_status = _status_for_level(payload["water"], critical_at=3.0, degraded_at=6.0)
    status = _worst_status((food_status, water_status))
    reason = "water_critical" if water_status == "critical" else "food_critical" if food_status == "critical" else "metabolic_degraded" if status == "degraded" else "metabolic_ok"
    return SensorOutput(
        dimension="avatar_metabolic",
        payload={
            **payload,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown"},
        },
    )


def _avatar_safety_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, threat_count = _avatar_life_payload(context)
    health_status = _status_for_level(payload["health"], critical_at=3.0, degraded_at=6.0)
    status = health_status
    if threat_count > 1:
        status = _worst_status((status, "critical"))
    elif threat_count == 1:
        status = _worst_status((status, "degraded"))
    reason = "health_critical" if health_status == "critical" else "threat_nearby" if threat_count else "health_degraded" if health_status == "degraded" else "avatar_safety_ok"
    return SensorOutput(
        dimension="avatar_safety",
        payload={
            **payload,
            "threat_count": threat_count,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown"},
        },
    )


def _avatar_recovery_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, _ = _avatar_life_payload(context)
    status = _status_for_level(payload["energy"], critical_at=3.0, degraded_at=6.0)
    reason = "energy_critical" if status == "critical" else "energy_degraded" if status == "degraded" else "recovery_ok"
    return SensorOutput(
        dimension="avatar_recovery",
        payload={
            **payload,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown"},
        },
    )


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _worst_status(statuses: object) -> str:
    order = {"healthy": 0, "degraded": 1, "critical": 2}
    current = "healthy"
    for status in statuses:
        if order.get(str(status), 0) > order[current]:
            current = str(status)
    return current


def build_avatar_state_sensor_specs() -> tuple[SensorSpec, ...]:
    from eva.l1_sensing.sensor_registry import SensorSpec

    return (
        SensorSpec(name="avatar_metabolic", collect=_avatar_metabolic_sensor),
        SensorSpec(name="avatar_safety", collect=_avatar_safety_sensor),
        SensorSpec(name="avatar_recovery", collect=_avatar_recovery_sensor),
    )


__all__ = ["build_avatar_state_sensor_specs"]
