"""Crafter inventory-state sensor specs for Stage H H-1."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec

KEY_RESOURCES = ("wood", "stone", "coal", "iron", "diamond", "sapling", "drink", "food")
TOOLS = ("wood_pickaxe", "stone_pickaxe", "iron_pickaxe", "wood_sword", "stone_sword", "iron_sword")


def _inventory_items(context: SensingContext) -> dict[str, object]:
    observation = context.shared_facts.get("agent_observation") or {}
    visible = observation.get("visible", {}) if isinstance(observation, dict) else {}
    inventory_panel = visible.get("inventory_panel", {}) if isinstance(visible, dict) else {}
    items = inventory_panel.get("items", {}) if isinstance(inventory_panel, dict) else {}
    return dict(items)


def _inventory_acquisition_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    items = _inventory_items(context)
    key_resources = {name: int(items.get(name, 0) or 0) for name in KEY_RESOURCES}
    scarce_resources = sorted(name for name, count in key_resources.items() if count <= 0)
    status = "critical" if len(scarce_resources) >= 4 else "degraded" if scarce_resources else "healthy"
    reason = "inventory_sparse" if status != "healthy" else "inventory_ok"
    return SensorOutput(
        dimension="inventory_acquisition",
        payload={
            "items": dict(items),
            "key_resources": key_resources,
            "scarce_resources": scarce_resources,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
        },
    )


def _inventory_capability_sensor(context: SensingContext) -> SensorOutput:
    from eva.l1_sensing.sensor_registry import SensorOutput

    items = _inventory_items(context)
    tools = {name: int(items.get(name, 0) or 0) for name in TOOLS}
    available_tools = sorted(name for name, count in tools.items() if count > 0)
    status = "degraded" if not available_tools else "healthy"
    reason = "tooling_missing" if status == "degraded" else "tooling_available"
    return SensorOutput(
        dimension="inventory_capability",
        payload={
            "items": dict(items),
            "tools": tools,
            "available_tools": available_tools,
            "status": status,
            "reason": reason,
            "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
        },
    )


def build_inventory_state_sensor_specs() -> tuple[SensorSpec, ...]:
    from eva.l1_sensing.sensor_registry import SensorSpec

    return (
        SensorSpec(name="inventory_acquisition", collect=_inventory_acquisition_sensor),
        SensorSpec(name="inventory_capability", collect=_inventory_capability_sensor),
    )


__all__ = ["build_inventory_state_sensor_specs"]
