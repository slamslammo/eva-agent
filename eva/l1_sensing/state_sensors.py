"""Compatibility wrappers for the current Linux runtime state sensors."""

from __future__ import annotations

from typing import Callable

from scenarios.linux_runtime.sensors import (
    build_anomaly_accumulation_sensor_specs as _build_anomaly_accumulation_sensor_specs,
    build_host_continuity_sensor_specs as _build_host_continuity_sensor_specs,
    build_resource_state_sensor_specs as _build_resource_state_sensor_specs,
    build_runtime_integrity_sensor_specs as _build_runtime_integrity_sensor_specs,
    linux_runtime_sensor_providers,
)

from .sensor_registry import SensorSpec

BuiltInSensorProvider = Callable[[], tuple[SensorSpec, ...]]

build_host_continuity_sensor_specs = _build_host_continuity_sensor_specs
build_runtime_integrity_sensor_specs = _build_runtime_integrity_sensor_specs
build_resource_state_sensor_specs = _build_resource_state_sensor_specs
build_anomaly_accumulation_sensor_specs = _build_anomaly_accumulation_sensor_specs


def built_in_sensor_providers() -> tuple[BuiltInSensorProvider, ...]:
    """Return the ordered built-in sensor providers for baseline L1 sensing."""

    return linux_runtime_sensor_providers()


def build_state_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the ordered baseline state-sensor specs for current L1 dimensions."""

    specs: list[SensorSpec] = []
    for provider in built_in_sensor_providers():
        specs.extend(provider())
    return tuple(specs)


__all__ = [
    "BuiltInSensorProvider",
    "build_anomaly_accumulation_sensor_specs",
    "build_host_continuity_sensor_specs",
    "build_resource_state_sensor_specs",
    "build_runtime_integrity_sensor_specs",
    "build_state_sensor_specs",
    "built_in_sensor_providers",
]
