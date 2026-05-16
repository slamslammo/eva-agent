"""Crafter local-view sensor specs for Stage H H-1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .inventory import KEY_RESOURCES, TOOLS

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec

THREATS = {"zombie", "skeleton", "arrow"}
RESOURCE_HINTS = {"tree", "stone", "coal", "iron", "diamond", "water", "plant"}
UTILITY_HINTS = {"table", "furnace"}


def _local_view_inputs(context: SensingContext) -> tuple[dict[str, int], dict[str, int], dict[str, int], list[str], list[str]]:
    observation = context.shared_facts.get("agent_observation") or {}
    visible = observation.get("visible", {}) if isinstance(observation, dict) else {}
    local_view = visible.get("local_view", {}) if isinstance(visible, dict) else {}
    inventory_panel = visible.get("inventory_panel", {}) if isinstance(visible, dict) else {}

    nearby_objects = local_view.get("nearby_objects", {}) if isinstance(local_view, dict) else {}
    nearby_materials = local_view.get("nearby_materials", {}) if isinstance(local_view, dict) else {}
    items = inventory_panel.get("items", {}) if isinstance(inventory_panel, dict) else {}

    threat_counts = {name: int(count) for name, count in nearby_objects.items() if name in THREATS}
    resource_counts = {name: int(count) for name, count in nearby_materials.items() if name in RESOURCE_HINTS}
    utility_counts = {name: int(count) for name, count in nearby_materials.items() if name in UTILITY_HINTS}

    key_resources = {name: int(items.get(name, 0) or 0) for name in KEY_RESOURCES}
    scarce_resources = sorted(name for name, count in key_resources.items() if count <= 0)
    tools = {name: int(items.get(name, 0) or 0) for name in TOOLS}
    available_tools = sorted(name for name, count in tools.items() if count > 0)
    return threat_counts, resource_counts, utility_counts, scarce_resources, available_tools


def _local_view_threat_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    threat_counts, _, _, _, _ = _local_view_inputs(context)
    threat_total = sum(threat_counts.values())
    status = "critical" if threat_total > 1 else "degraded" if threat_total == 1 else "healthy"
    reason = "threat_visible" if threat_total else "local_threat_clear"
    return SensorOutput(
        dimension="local_view_threat",
        payload={
            "threat_counts": threat_counts,
            "threat_total": threat_total,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
        },
    )


def _local_view_resource_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    _, resource_counts, _, scarce_resources, _ = _local_view_inputs(context)
    resource_total = sum(resource_counts.values())
    scarcity_count = len(scarce_resources)
    status = "critical" if resource_total and scarcity_count >= 4 else "degraded" if resource_total and scarcity_count > 0 else "healthy"
    reason = "resource_visible" if status != "healthy" else "local_resource_clear"
    return SensorOutput(
        dimension="local_view_resource",
        payload={
            "resource_counts": resource_counts,
            "resource_total": resource_total,
            "scarce_resources": scarce_resources,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
        },
    )


def _local_view_utility_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    _, _, utility_counts, _, available_tools = _local_view_inputs(context)
    utility_total = sum(utility_counts.values())
    capability_gap = not available_tools
    status = "critical" if utility_total and capability_gap else "degraded" if utility_total else "healthy"
    reason = "utility_visible" if utility_total else "local_utility_clear"
    return SensorOutput(
        dimension="local_view_utility",
        payload={
            "utility_counts": utility_counts,
            "utility_total": utility_total,
            "available_tools": available_tools,
            "capability_gap": capability_gap,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
        },
    )


def build_local_view_sensor_specs() -> tuple[SensorSpec, ...]:
    from eva.l1_sensing.sensor_registry import SensorSpec

    return (
        SensorSpec(name="local_view_threat", collect=_local_view_threat_sensor),
        SensorSpec(name="local_view_resource", collect=_local_view_resource_sensor),
        SensorSpec(name="local_view_utility", collect=_local_view_utility_sensor),
    )


__all__ = ["build_local_view_sensor_specs"]
