"""Auditable Crafter perception packet for L3 reasoning context.

PR-1 boundary: this module copies bounded observation facts for L3. It never
orders actions or recommends an action.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .world_facts import CRAFTER_WORLD_FACTS_REF

SCHEMA_VERSION = "crafter_state_packet_v1"
FOOD_CELLS = frozenset({"cow", "plant"})
THREAT_CELLS = frozenset({"zombie", "skeleton", "arrow"})

__all__ = ["SCHEMA_VERSION", "build_crafter_state_packet"]


def build_crafter_state_packet(
    agent_observation: Mapping[str, Any] | None,
    *,
    drive_broadcast: Mapping[str, Any] | None = None,
    working_memory_context: Mapping[str, Any] | None = None,
    available_actions: Sequence[str] | None = None,
    raw_observation_ref: str | None = None,
) -> dict[str, Any]:
    """Build the bounded perception packet consumed by Crafter L3 prompting."""

    observation = agent_observation if isinstance(agent_observation, Mapping) else {}
    visible = _mapping(observation.get("visible"))
    local_view = _mapping(visible.get("local_view"))
    cells = _cells(local_view.get("cells"))
    life = _life_values(_mapping(_mapping(visible.get("life_panel")).get("values")))
    inventory = _inventory(_mapping(_mapping(visible.get("inventory_panel")).get("items")))
    center = _center(local_view.get("center"), cells)

    return {
        "schema_version": SCHEMA_VERSION,
        "raw_observation_ref": raw_observation_ref or _default_raw_observation_ref(observation),
        "life": life,
        "rates": _rates(working_memory_context),
        "facing": str(visible.get("facing") or "unknown"),
        "local_view": {
            "format": str(local_view.get("format") or "unknown"),
            "width": _int_or_len(local_view.get("width"), cells[0] if cells else []),
            "height": _int_or_len(local_view.get("height"), cells),
            "center": center,
            "cells": cells,
        },
        "inventory": inventory,
        "visible": {
            "water": _locations(cells, center, {"water"}),
            "food": _locations(cells, center, FOOD_CELLS),
            "threats": _locations(cells, center, THREAT_CELLS),
        },
        "salience": _salience(life, drive_broadcast),
        "recent_outcomes": _recent_outcomes(working_memory_context),
        "available_actions": _action_list(
            available_actions if available_actions is not None else observation.get("available_actions")
        ),
        "world_facts_ref": CRAFTER_WORLD_FACTS_REF,
    }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _life_values(values: Mapping[str, Any]) -> dict[str, float | None]:
    return {
        "health": _float_or_none(values.get("health")),
        "food": _float_or_none(values.get("food")),
        "water": _float_or_none(values.get("water")),
        "energy": _float_or_none(values.get("energy")),
    }


def _inventory(items: Mapping[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, value in items.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            out[str(key)] = int(value)
    return out


def _cells(value: object) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    rows: list[list[str]] = []
    for row in value:
        if isinstance(row, list):
            rows.append([str(cell) for cell in row])
    return rows


def _center(value: object, cells: list[list[str]]) -> dict[str, int]:
    if isinstance(value, Mapping):
        col = _int(value.get("col"))
        row = _int(value.get("row"))
        if col is not None and row is not None:
            return {"col": col, "row": row}
    height = len(cells)
    width = len(cells[0]) if cells else 0
    return {"col": width // 2 if width else 0, "row": height // 2 if height else 0}


def _locations(
    cells: list[list[str]],
    center: Mapping[str, int],
    names: Iterable[str],
) -> list[dict[str, Any]]:
    wanted = set(names)
    center_row = int(center.get("row", 0))
    center_col = int(center.get("col", 0))
    locations: list[dict[str, Any]] = []
    for row_index, row in enumerate(cells):
        for col_index, cell in enumerate(row):
            if cell not in wanted:
                continue
            locations.append(
                {
                    "kind": cell,
                    "row": row_index,
                    "col": col_index,
                    "offset": {
                        "row": row_index - center_row,
                        "col": col_index - center_col,
                    },
                }
            )
    return locations


def _salience(
    life: Mapping[str, float | None],
    drive_broadcast: Mapping[str, Any] | None,
) -> dict[str, Any]:
    drive = drive_broadcast if isinstance(drive_broadcast, Mapping) else {}
    drive_levels = drive.get("drive_levels")
    salience = {
        "top_drive": drive.get("top_drive"),
        "drive_levels": dict(drive_levels) if isinstance(drive_levels, Mapping) else {},
        "thirst": _life_status(life.get("water")),
        "hunger": _life_status(life.get("food")),
        "safety": _life_status(life.get("health")),
        "recovery": _life_status(life.get("energy")),
    }
    return salience


def _life_status(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value <= 3.0:
        return "critical"
    if value <= 6.0:
        return "degraded"
    return "stable"


def _rates(working_memory_context: Mapping[str, Any] | None) -> dict[str, float]:
    wm = working_memory_context if isinstance(working_memory_context, Mapping) else {}
    raw = wm.get("crafter_rates") or wm.get("rates") or {}
    if not isinstance(raw, Mapping):
        return {}
    rates: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            rates[str(key)] = float(value)
    return rates


def _recent_outcomes(working_memory_context: Mapping[str, Any] | None) -> list[str]:
    wm = working_memory_context if isinstance(working_memory_context, Mapping) else {}
    raw = wm.get("recent_relevant_outcomes")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw[:3]:
        if isinstance(item, str):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            continue
        action = item.get("selected_action") or item.get("action")
        outcome = item.get("pressure_outcome") or item.get("outcome") or item.get("result")
        if action and outcome:
            out.append(f"{action} -> {outcome}")
    return out


def _action_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(action) for action in value]
    return []


def _default_raw_observation_ref(observation: Mapping[str, Any]) -> str:
    schema = str(observation.get("schema_version") or "agent_observation")
    episode_id = observation.get("episode_id")
    step = observation.get("step")
    if episode_id is not None and step is not None:
        return f"{schema}:episode={episode_id}:step={step}"
    if step is not None:
        return f"{schema}:step={step}"
    return schema


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_len(value: object, default_items: Sequence[Any]) -> int:
    return _int(value) or len(default_items)
