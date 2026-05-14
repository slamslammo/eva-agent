"""Compatibility wrappers for the active runtime concrete state sensors."""

from __future__ import annotations

from typing import Callable

from ..scenario_bundle import get_active_runtime_scenario
from .sensor_registry import SensorSpec

BuiltInSensorProvider = Callable[[], tuple[SensorSpec, ...]]


def _active_sensors():
    return get_active_runtime_scenario().sensors


def built_in_sensor_providers() -> tuple[BuiltInSensorProvider, ...]:
    """Return the ordered built-in sensor providers for baseline L1 sensing."""

    return _active_sensors().sensor_providers()


def build_state_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the ordered baseline state-sensor specs for current L1 dimensions."""

    specs: list[SensorSpec] = []
    for provider in built_in_sensor_providers():
        specs.extend(provider())
    return tuple(specs)


__all__ = [
    "BuiltInSensorProvider",
    "build_state_sensor_specs",
    "built_in_sensor_providers",
]
