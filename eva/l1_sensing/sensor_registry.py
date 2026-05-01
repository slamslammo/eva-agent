"""Minimal sensor registry primitives for L1 sensing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Sequence

from ..kernel import ExternalLifeConfig, ExternalLifeSnapshot, RuntimeState, StateStore

SensorCollector = Callable[["SensingContext"], "SensorOutput"]


@dataclass(frozen=True)
class SensorSpec:
    """One registered L1 sensor collector."""

    name: str
    collect: SensorCollector


@dataclass(frozen=True)
class SensorOutput:
    """One normalized sensor output before judgment."""

    dimension: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class SensingContext:
    """Shared sampling context for one sensing pass."""

    store: StateStore
    runtime_state: RuntimeState
    config: ExternalLifeConfig
    now: datetime
    due_at: datetime | None = None
    previous_snapshot: ExternalLifeSnapshot | None = None
    shared_facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SensorRegistry:
    """Small ordered registry of L1 sensor specs."""

    sensors: tuple[SensorSpec, ...]

    def collect_all(self, context: SensingContext) -> list[SensorOutput]:
        """Collect outputs from all registered sensors in order."""

        return [sensor.collect(context) for sensor in self.sensors]


def build_sensor_registry(sensors: Sequence[SensorSpec]) -> SensorRegistry:
    """Freeze a sensor sequence into the canonical registry object."""

    return SensorRegistry(sensors=tuple(sensors))
