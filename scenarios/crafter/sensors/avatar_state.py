"""Crafter avatar-state sensor specs for Stage H H-1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from eva.l1_sensing.rate_sensors import (
    aggregate_change_magnitude,
    build_rate_context,
    combine_directions,
    metric_change,
    previous_dimension_evidence,
    previous_rate_context,
    unavailable_rate_context,
)

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


def _avatar_life_payload(context: SensingContext) -> tuple[dict[str, float | None], int, str | None]:
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
    episode_id = observation.get("episode_id") if isinstance(observation, dict) else None
    return payload, threat_count, str(episode_id) if episode_id is not None else None


def _elapsed_sec(context: SensingContext) -> float | None:
    value = context.shared_facts.get("elapsed_sec")
    return _coerce_float(value)


def _episode_matches(previous_evidence: dict[str, object], episode_id: str | None) -> bool:
    previous_episode_id = previous_evidence.get("episode_id")
    if episode_id is None or previous_episode_id is None:
        return True
    return str(previous_episode_id) == episode_id


def _rate_context_for_metrics(
    context: SensingContext,
    dimension_name: str,
    episode_id: str | None,
    metrics: dict[str, tuple[float | None, bool]],
) -> dict[str, object]:
    elapsed_sec = _elapsed_sec(context)
    previous_evidence = previous_dimension_evidence(context.previous_snapshot, dimension_name)
    if not bool(context.shared_facts.get("rate_available")) or elapsed_sec is None or elapsed_sec <= 0:
        return unavailable_rate_context()
    if not previous_evidence or not _episode_matches(previous_evidence, episode_id):
        return unavailable_rate_context()

    changes: list[dict[str, object]] = []
    extra: dict[str, object] = {"elapsed_sec": elapsed_sec}
    for metric_name, (current_value, higher_is_worse) in metrics.items():
        change = (
            metric_change(
                current_value,
                _coerce_float(previous_evidence.get(metric_name)),
                elapsed_sec,
                higher_is_worse=higher_is_worse,
            )
            if current_value is not None
            else {"delta": None, "direction": "unknown", "change_per_sec": None}
        )
        changes.append(change)
        extra[f"{metric_name}_delta"] = change["delta"]
        extra[f"{metric_name}_change_per_sec"] = change["change_per_sec"]
        extra[f"{metric_name}_direction"] = change["direction"]

    return build_rate_context(
        available=True,
        direction=combine_directions(*(str(change["direction"]) for change in changes)),
        raw_magnitude=aggregate_change_magnitude(*changes),
        previous_rate=previous_rate_context(context.previous_snapshot, dimension_name),
        aggregation_method="ewma",
        extra=extra,
    )


def _avatar_metabolic_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, _, episode_id = _avatar_life_payload(context)
    food_status = _status_for_level(payload["food"], critical_at=3.0, degraded_at=6.0)
    water_status = _status_for_level(payload["water"], critical_at=3.0, degraded_at=6.0)
    status = _worst_status((food_status, water_status))
    reason = "water_critical" if water_status == "critical" else "food_critical" if food_status == "critical" else "metabolic_degraded" if status == "degraded" else "metabolic_ok"
    return SensorOutput(
        dimension="avatar_metabolic",
        payload={
            **payload,
            "episode_id": episode_id,
            "status": status,
            "reason": reason,
            "rate_context": _rate_context_for_metrics(
                context,
                "avatar_metabolic",
                episode_id,
                {
                    "food": (payload["food"], False),
                    "water": (payload["water"], False),
                },
            ),
        },
    )


def _avatar_safety_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, threat_count, episode_id = _avatar_life_payload(context)
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
            "episode_id": episode_id,
            "threat_count": threat_count,
            "status": status,
            "reason": reason,
            "rate_context": _rate_context_for_metrics(
                context,
                "avatar_safety",
                episode_id,
                {
                    "health": (payload["health"], False),
                    "threat_count": (float(threat_count), True),
                },
            ),
        },
    )


def _avatar_recovery_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    payload, _, episode_id = _avatar_life_payload(context)
    status = _status_for_level(payload["energy"], critical_at=3.0, degraded_at=6.0)
    reason = "energy_critical" if status == "critical" else "energy_degraded" if status == "degraded" else "recovery_ok"
    return SensorOutput(
        dimension="avatar_recovery",
        payload={
            **payload,
            "episode_id": episode_id,
            "status": status,
            "reason": reason,
            "rate_context": _rate_context_for_metrics(
                context,
                "avatar_recovery",
                episode_id,
                {"energy": (payload["energy"], False)},
            ),
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
