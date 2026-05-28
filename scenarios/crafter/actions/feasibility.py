"""Per-turn action feasibility for the Crafter anchor and LLM producer.

World-layer feasibility only — an action is dropped iff the world makes it
impossible right now (missing materials / no nearby table·furnace per Crafter's
recipe requirements in crafter/data.yaml). Actions with no material requirement
(noop / sleep / move_* / do) are always feasible.
"""

from __future__ import annotations

from typing import Any, Mapping

from .registry import CRAFTER_ACTIONS

# Crafter recipe requirements (crafter/data.yaml ``place`` + ``make`` tables).
# action -> {"uses": {inventory_item: min_count}, "nearby": (material, ...)}.
# Only these gate on the world; every other action is always feasible.
_CRAFT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "place_stone": {"uses": {"stone": 1}, "nearby": ()},
    "place_table": {"uses": {"wood": 2}, "nearby": ()},
    "place_furnace": {"uses": {"stone": 4}, "nearby": ()},
    "place_plant": {"uses": {"sapling": 1}, "nearby": ()},
    "make_wood_pickaxe": {"uses": {"wood": 1}, "nearby": ("table",)},
    "make_stone_pickaxe": {"uses": {"wood": 1, "stone": 1}, "nearby": ("table",)},
    "make_iron_pickaxe": {"uses": {"wood": 1, "coal": 1, "iron": 1}, "nearby": ("table", "furnace")},
    "make_wood_sword": {"uses": {"wood": 1}, "nearby": ("table",)},
    "make_stone_sword": {"uses": {"wood": 1, "stone": 1}, "nearby": ("table",)},
    "make_iron_sword": {"uses": {"wood": 1, "coal": 1, "iron": 1}, "nearby": ("table", "furnace")},
}

__all__ = ["feasible_raw_actions", "action_is_feasible"]


def _inventory(observation: Mapping[str, Any] | None) -> dict[str, int]:
    visible = observation.get("visible") if isinstance(observation, Mapping) else None
    panel = visible.get("inventory_panel") if isinstance(visible, Mapping) else None
    items = panel.get("items") if isinstance(panel, Mapping) else None
    out: dict[str, int] = {}
    if isinstance(items, Mapping):
        for key, value in items.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out[str(key)] = int(value)
    return out


def _nearby_cell_names(observation: Mapping[str, Any] | None) -> set[str]:
    """Names present in the local view (over-approximates Crafter's adjacency 'nearby').

    Conservative on purpose: an action is only filtered when the required material is
    *entirely absent* from view (definitely cannot make this turn). If a table/furnace
    is in view but not yet adjacent the action is kept (the LLM may approach) — that
    avoids ever over-filtering a possibly-feasible action.
    """

    visible = observation.get("visible") if isinstance(observation, Mapping) else None
    local_view = visible.get("local_view") if isinstance(visible, Mapping) else None
    cells = local_view.get("cells") if isinstance(local_view, Mapping) else None
    names: set[str] = set()
    if isinstance(cells, list):
        for row in cells:
            if isinstance(row, list):
                names.update(str(cell) for cell in row)
    return names


def action_is_feasible(action: str, inventory: Mapping[str, int], nearby: set[str]) -> bool:
    """True iff the action can physically succeed now (no usefulness judgement)."""

    requirement = _CRAFT_REQUIREMENTS.get(action)
    if requirement is None:
        return True  # noop / sleep / move_* / do — no material requirement
    for item, count in requirement["uses"].items():
        if inventory.get(item, 0) < count:
            return False
    for material in requirement["nearby"]:
        if material not in nearby:
            return False
    return True


def feasible_raw_actions(observation: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Return raw Crafter actions that are physically possible right now.

    World-layer feasibility only. Drops actions only when the world facts make them
    impossible now (missing materials / missing visible table or furnace for recipes).
    Does not judge whether an action is wise.
    """

    inventory = _inventory(observation)
    nearby = _nearby_cell_names(observation)
    return tuple(action for action in CRAFTER_ACTIONS if action_is_feasible(action, inventory, nearby))
