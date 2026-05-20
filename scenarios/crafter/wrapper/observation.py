"""Agent-facing symbolic observation v0 for Crafter H-0."""

from __future__ import annotations

from typing import Any, Mapping

from .evaluator_surface import extract_achievements, extract_inventory, extract_life, jsonable
from .semantic_local_view import build_local_view, compact_grid
from ..actions import CRAFTER_ACTIONS


def observation_shape(raw_observation: Any) -> list[int] | None:
    shape = getattr(raw_observation, "shape", None)
    if shape is not None:
        return list(shape)
    if isinstance(raw_observation, (list, tuple)):
        return [len(raw_observation)]
    return None


def build_symbolic_observation(
    *,
    episode_id: str,
    step: int,
    raw_observation: Any,
    raw_info: Mapping[str, Any] | None,
    observation_mode: str = "visible_state_proxy",
    facing: str = "unknown",
) -> dict[str, Any]:
    info = dict(raw_info or {})
    achievements = extract_achievements(info)
    unlocked = [name for name, value in achievements.items() if bool(value)]
    local_view = build_local_view(info)
    nearby_objects = sorted(local_view.get("nearby_objects", {}).keys())
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": episode_id,
        "step": step,
        "visible": {
            "local_view": local_view,
            "life_panel": {
                "available": any(value is not None for value in extract_life(info).values()),
                "values": jsonable(extract_life(info)),
            },
            "inventory_panel": {
                "available": bool(extract_inventory(info)),
                "items": jsonable(extract_inventory(info)),
            },
            # Crafter does not surface facing in ``info``; the wrapper supplies it
            # (tracked from the last movement direction). Fall back to info/unknown.
            "facing": facing if facing and facing != "unknown" else info.get("facing", "unknown"),
            "nearby_objects": nearby_objects,
        },
        "task_context": {
            "objective": "survive and unlock achievements",
            "known_achievements": list(achievements.keys()),
            "unlocked_achievements_visible": unlocked,
        },
        "available_actions": list(CRAFTER_ACTIONS),
        "notes": [
            f"observation_mode={observation_mode}",
            f"raw_observation_shape={observation_shape(raw_observation)}",
            f"local_view_source={local_view.get('source')}",
            "compact_grid:\n" + compact_grid(local_view.get("cells") or []),
        ],
    }


__all__ = ["build_symbolic_observation", "observation_shape"]
