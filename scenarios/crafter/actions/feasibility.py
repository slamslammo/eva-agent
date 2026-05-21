"""Round 1.I (a2): per-turn action feasibility for the live dlPFC producer.

Filters the static ``PROFILE_ELIGIBLE_ACTIONS`` down to the actions that can
*physically* succeed given the current Crafter observation, per Crafter's own recipe
requirements (``crafter/data.yaml``: each ``make_*`` / ``place_*`` lists the inventory
``uses`` it consumes and, for ``make_*``, the ``nearby`` materials it needs).

This is **World-layer feasibility only** — an action is dropped iff the world makes it
impossible right now (missing materials / no nearby table·furnace). It is **never**
dropped for being unwise / unhelpful / off-strategy — that is Behavior-layer policy and
stays the LLM's job (round-1i A red-line ④). Actions with no material requirement
(``noop`` / ``sleep`` / ``move_*`` / ``do``) are always feasible, so every posture keeps
at least its default action and the feasible set is never empty.

The producer stays framework-generic: the runtime injects ``feasible_profile_action_vocab``
(closed over the live session) as a per-turn vocab callable; the producer never imports
this module.
"""

from __future__ import annotations

from typing import Any, Mapping

from .compatibility import PROFILE_DEFAULT_ACTION, PROFILE_ELIGIBLE_ACTIONS

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

__all__ = ["feasible_profile_action_vocab", "action_is_feasible"]


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


def feasible_profile_action_vocab(
    observation: Mapping[str, Any] | None,
) -> dict[str, tuple[str, ...]]:
    """Per-posture vocab keeping only world-feasible actions (default always kept)."""

    inventory = _inventory(observation)
    nearby = _nearby_cell_names(observation)
    vocab: dict[str, tuple[str, ...]] = {}
    for profile, actions in PROFILE_ELIGIBLE_ACTIONS.items():
        feasible = tuple(a for a in actions if action_is_feasible(a, inventory, nearby))
        # Empty-set fallback (round-1i A condition ②): the posture default is itself
        # always-feasible (noop/sleep/do) — guarantee it is present even if upstream
        # eligibility ever omitted it, so a posture never collapses to no options.
        default = PROFILE_DEFAULT_ACTION.get(profile)
        if default and default not in feasible:
            feasible = (default,) + feasible
        vocab[profile] = feasible
    return vocab
