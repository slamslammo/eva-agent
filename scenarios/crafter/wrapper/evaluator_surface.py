"""Evaluator-only Crafter surface extraction for H-0 fairness boundaries."""

from __future__ import annotations

import json
from typing import Any, Mapping


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            return value.tolist()
        except Exception:
            pass
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _first_mapping(info: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    for key in keys:
        value = info.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def extract_inventory(info: Mapping[str, Any]) -> dict[str, Any]:
    return _first_mapping(info, ("inventory", "items"))


def extract_achievements(info: Mapping[str, Any]) -> dict[str, Any]:
    return _first_mapping(info, ("achievements", "achievement"))


def extract_life(info: Mapping[str, Any]) -> dict[str, Any | None]:
    life = _first_mapping(info, ("life", "status", "player"))
    inventory = extract_inventory(info)
    return {
        "health": life.get("health", info.get("health", inventory.get("health"))),
        "food": life.get("food", info.get("food", inventory.get("food"))),
        "water": life.get("water", info.get("water", inventory.get("water", inventory.get("drink")))) ,
        "energy": life.get("energy", info.get("energy", inventory.get("energy"))),
    }


__all__ = ["extract_achievements", "extract_inventory", "extract_life", "jsonable"]
