"""Crafter action names, ids, and lightweight H-0 metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

CRAFTER_ACTIONS: tuple[str, ...] = (
    "noop",
    "move_left",
    "move_right",
    "move_up",
    "move_down",
    "do",
    "sleep",
    "place_stone",
    "place_table",
    "place_furnace",
    "place_plant",
    "make_wood_pickaxe",
    "make_stone_pickaxe",
    "make_iron_pickaxe",
    "make_wood_sword",
    "make_stone_sword",
    "make_iron_sword",
)

ACTION_METADATA: dict[str, dict[str, object]] = {
    "noop": {
        "category": "idle",
        "reversibility": "high",
        "side_effect_class": "idle",
    },
    "move_left": {
        "category": "move",
        "reversibility": "high",
        "side_effect_class": "movement",
    },
    "move_right": {
        "category": "move",
        "reversibility": "high",
        "side_effect_class": "movement",
    },
    "move_up": {
        "category": "move",
        "reversibility": "high",
        "side_effect_class": "movement",
    },
    "move_down": {
        "category": "move",
        "reversibility": "high",
        "side_effect_class": "movement",
    },
    "do": {
        "category": "interact",
        "reversibility": "medium",
        "side_effect_class": "interaction",
    },
    "sleep": {
        "category": "recovery",
        "reversibility": "medium",
        "side_effect_class": "recovery",
    },
    "place_stone": {
        "category": "place",
        "reversibility": "low",
        "side_effect_class": "placement",
    },
    "place_table": {
        "category": "place",
        "reversibility": "low",
        "side_effect_class": "placement",
    },
    "place_furnace": {
        "category": "place",
        "reversibility": "low",
        "side_effect_class": "placement",
    },
    "place_plant": {
        "category": "place",
        "reversibility": "low",
        "side_effect_class": "placement",
    },
}

for _name in CRAFTER_ACTIONS:
    ACTION_METADATA.setdefault(
        _name,
        {
            "category": "craft",
            "reversibility": "low",
            "side_effect_class": "crafting",
        },
    )


@dataclass(frozen=True)
class ActionAdapter:
    """String/id conversion layer for Crafter actions."""

    actions: tuple[str, ...] = CRAFTER_ACTIONS

    def name_to_id(self, name: str) -> int:
        if name not in self.actions:
            raise ValueError(f"Invalid action {name!r}; expected one of {list(self.actions)!r}")
        return self.actions.index(name)

    def id_to_name(self, action_id: int) -> str:
        if action_id < 0 or action_id >= len(self.actions):
            raise ValueError(f"Invalid action id {action_id}; expected [0, {len(self.actions) - 1}]")
        return self.actions[action_id]

    def validate_env_action_space(self, env_action_space: object) -> Mapping[str, object]:
        env_count = getattr(env_action_space, "n", None)
        return {
            "expected_action_count": len(self.actions),
            "env_action_count": env_count,
            "matches_expected": env_count == len(self.actions),
            "actions": list(self.actions),
        }

    def metadata(self, name: str) -> Mapping[str, object]:
        self.name_to_id(name)
        return ACTION_METADATA[name]


def action_names() -> Iterable[str]:
    return CRAFTER_ACTIONS


__all__ = ["ACTION_METADATA", "CRAFTER_ACTIONS", "ActionAdapter", "action_names"]
