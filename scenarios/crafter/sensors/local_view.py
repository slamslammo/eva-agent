"""Crafter local-view sensor specs for Stage H H-1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec

THREATS = {"zombie", "skeleton", "arrow"}
RESOURCE_HINTS = {"tree", "stone", "coal", "iron", "diamond", "water", "plant"}
UTILITY_HINTS = {"table", "furnace"}


def _local_view_state_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    observation = context.shared_facts.get("agent_observation") or {}
    visible = observation.get("visible", {}) if isinstance(observation, dict) else {}
    local_view = visible.get("local_view", {}) if isinstance(visible, dict) else {}

    nearby_objects = local_view.get("nearby_objects", {}) if isinstance(local_view, dict) else {}
    nearby_materials = local_view.get("nearby_materials", {}) if isinstance(local_view, dict) else {}
    threat_counts = {name: int(count) for name, count in nearby_objects.items() if name in THREATS}
    resource_counts = {name: int(count) for name, count in nearby_materials.items() if name in RESOURCE_HINTS}
    utility_counts = {name: int(count) for name, count in nearby_materials.items() if name in UTILITY_HINTS}
    threat_total = sum(threat_counts.values())
    status = "critical" if threat_total > 1 else "degraded" if threat_total == 1 else "healthy"
    reason = "threat_visible" if threat_total else "local_view_ok"

    return SensorOutput(
        dimension="local_view_state",
        payload={
            "threat_counts": threat_counts,
            "resource_counts": resource_counts,
            "utility_counts": utility_counts,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown"},
        },
    )


def build_local_view_state_sensor_specs() -> tuple[SensorSpec, ...]:
    from eva.l1_sensing.sensor_registry import SensorSpec

    return (SensorSpec(name="local_view_state", collect=_local_view_state_sensor),)


__all__ = ["build_local_view_state_sensor_specs"]
