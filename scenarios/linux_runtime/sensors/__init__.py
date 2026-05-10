"""Linux runtime concrete sensor providers for Phase A."""

from __future__ import annotations

from typing import Callable

from .anomaly import build_anomaly_accumulation_sensor_specs
from .heartbeat import build_host_continuity_sensor_specs
from .resource import build_resource_state_sensor_specs
from .runtime import build_runtime_integrity_sensor_specs

LinuxRuntimeSensorProvider = Callable[[], tuple[object, ...]]


def linux_runtime_sensor_providers() -> tuple[LinuxRuntimeSensorProvider, ...]:
    """Return the ordered Linux runtime sensor providers."""

    return (
        build_host_continuity_sensor_specs,
        build_runtime_integrity_sensor_specs,
        build_resource_state_sensor_specs,
        build_anomaly_accumulation_sensor_specs,
    )


__all__ = [
    "LinuxRuntimeSensorProvider",
    "build_anomaly_accumulation_sensor_specs",
    "build_host_continuity_sensor_specs",
    "build_resource_state_sensor_specs",
    "build_runtime_integrity_sensor_specs",
    "linux_runtime_sensor_providers",
]
