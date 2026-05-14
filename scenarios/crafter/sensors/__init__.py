"""Crafter sensor providers for Stage H H-1."""

from __future__ import annotations

from typing import Callable

from .avatar_state import build_avatar_state_sensor_specs
from .inventory import build_inventory_state_sensor_specs
from .local_view import build_local_view_state_sensor_specs

CrafterSensorProvider = Callable[[], tuple[object, ...]]


def crafter_sensor_providers() -> tuple[CrafterSensorProvider, ...]:
    return (
        build_avatar_state_sensor_specs,
        build_inventory_state_sensor_specs,
        build_local_view_state_sensor_specs,
    )


__all__ = [
    "CrafterSensorProvider",
    "build_avatar_state_sensor_specs",
    "build_inventory_state_sensor_specs",
    "build_local_view_state_sensor_specs",
    "crafter_sensor_providers",
]
