"""Build a fair local symbolic view from Crafter semantic payloads."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import numpy as np

DEFAULT_VIEW = (9, 9)
OBJECT_NAMES = ("player", "cow", "zombie", "skeleton", "arrow", "plant")
OBJECT_SET = set(OBJECT_NAMES)


@dataclass(frozen=True)
class LocalViewSpec:
    width: int
    height: int
    center_col: int
    center_row: int

    @classmethod
    def from_crafter_view(cls, view: tuple[int, int] = DEFAULT_VIEW, item_count: int = 16) -> "LocalViewSpec":
        item_rows = int(math.ceil(item_count / view[0]))
        width = int(view[0])
        height = int(view[1] - item_rows)
        return cls(width=width, height=height, center_col=width // 2, center_row=height // 2)


def id_to_name_map() -> dict[int, str]:
    materials = [
        "water",
        "grass",
        "stone",
        "path",
        "sand",
        "tree",
        "lava",
        "coal",
        "iron",
        "diamond",
        "table",
        "furnace",
    ]
    try:
        from crafter import constants

        materials = list(constants.materials)
    except Exception:
        pass
    mapping = {index: name for index, name in enumerate([None] + materials) if name is not None}
    object_offset = len([None] + materials)
    for offset, name in enumerate(OBJECT_NAMES):
        mapping[object_offset + offset] = name
    return mapping


def build_local_view(
    info: Mapping[str, Any],
    *,
    view: tuple[int, int] = DEFAULT_VIEW,
) -> dict[str, Any]:
    semantic = info.get("semantic")
    player_pos = info.get("player_pos")
    if semantic is None or player_pos is None:
        return _unknown_view("missing semantic or player_pos")

    semantic_array = np.asarray(semantic)
    player = np.asarray(player_pos, dtype=int)
    if semantic_array.ndim != 2 or player.shape[0] < 2:
        return _unknown_view("unexpected semantic/player_pos shape")

    spec = LocalViewSpec.from_crafter_view(view=view)
    mapping = id_to_name_map()
    cells: list[list[str]] = []
    cell_ids: list[list[int | None]] = []

    for row in range(spec.height):
        dy = row - spec.center_row
        cell_row: list[str] = []
        id_row: list[int | None] = []
        for col in range(spec.width):
            dx = col - spec.center_col
            x = int(player[0] + dx)
            y = int(player[1] + dy)
            if x < 0 or y < 0 or x >= semantic_array.shape[0] or y >= semantic_array.shape[1]:
                cell_row.append("out_of_bounds")
                id_row.append(None)
                continue
            semantic_id = int(semantic_array[x, y])
            cell_row.append(mapping.get(semantic_id, f"unknown_{semantic_id}"))
            id_row.append(semantic_id)
        cells.append(cell_row)
        cell_ids.append(id_row)

    summary = summarize_cells(cells)
    return {
        "format": "semantic_grid",
        "source": "semantic_local_crop",
        "width": spec.width,
        "height": spec.height,
        "radius": {"x": spec.center_col, "y": spec.center_row},
        "center": {"col": spec.center_col, "row": spec.center_row},
        "cells": cells,
        "cell_ids": cell_ids,
        "nearby_objects": summary["objects"],
        "nearby_materials": summary["materials"],
        "notes": [
            "full semantic is wrapper/evaluator-only",
            "agent receives only this cropped local view",
        ],
    }


def summarize_cells(cells: Iterable[Iterable[str]]) -> dict[str, dict[str, int]]:
    counts = Counter(cell for row in cells for cell in row)
    objects = {name: counts[name] for name in sorted(OBJECT_SET & set(counts)) if name != "player"}
    materials = {
        name: count
        for name, count in sorted(counts.items())
        if name not in OBJECT_SET and not name.startswith("unknown")
    }
    return {"objects": objects, "materials": materials}


def compact_grid(cells: list[list[str]]) -> str:
    legend = {
        "water": "W",
        "grass": "G",
        "stone": "S",
        "path": "P",
        "sand": "A",
        "tree": "T",
        "lava": "L",
        "coal": "C",
        "iron": "I",
        "diamond": "D",
        "table": "B",
        "furnace": "F",
        "player": "@",
        "cow": "O",
        "zombie": "Z",
        "skeleton": "K",
        "arrow": ">",
        "plant": "+",
        "out_of_bounds": "X",
    }
    return "\n".join("".join(legend.get(cell, "?") for cell in row) for row in cells)


def validate_agent_local_view(agent_observation: Mapping[str, Any]) -> dict[str, Any]:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add(
        "no_full_semantic_in_agent_observation",
        not _has_forbidden_key(agent_observation, {"semantic", "raw_info"}),
        "agent observation should not contain full semantic/raw_info keys",
    )
    add(
        "no_absolute_player_pos_in_agent_observation",
        not _has_forbidden_key(agent_observation, {"player_pos", "position"}),
        "agent observation should not contain absolute player_pos/position keys",
    )
    return {
        "schema_version": "local_view_validation_v0",
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def _has_forbidden_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in forbidden or _has_forbidden_key(item, forbidden):
                return True
    elif isinstance(value, list):
        return any(_has_forbidden_key(item, forbidden) for item in value)
    return False


def _unknown_view(reason: str) -> dict[str, Any]:
    return {
        "format": "unknown",
        "source": "unavailable",
        "width": 0,
        "height": 0,
        "radius": None,
        "center": None,
        "cells": [],
        "cell_ids": [],
        "nearby_objects": {},
        "nearby_materials": {},
        "notes": [reason],
    }


__all__ = ["DEFAULT_VIEW", "build_local_view", "compact_grid", "validate_agent_local_view"]
