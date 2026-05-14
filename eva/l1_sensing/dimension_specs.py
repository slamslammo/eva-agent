"""Scenario-owned dimension specification seam for framework judgment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..kernel import DimensionSnapshot, ExternalLifeConfig

DimensionSnapshotFn = Callable[[dict[str, object], ExternalLifeConfig], DimensionSnapshot]


@dataclass(frozen=True)
class DimensionSpec:
    """One scenario-registered dimension judgment spec."""

    name: str
    priority: int
    pressure_type: str
    snapshot_fn: DimensionSnapshotFn


_DEFAULT_DIMENSION_SPECS: tuple[DimensionSpec, ...] = ()
_DEFAULT_DIMENSION_PRIORITY_BY_NAME: dict[str, int] = {}
_DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME: dict[str, str] = {}


def register_default_dimension_specs(specs: tuple[DimensionSpec, ...]) -> None:
    """Register the active dimension judgment specs for the current runtime context."""

    global _DEFAULT_DIMENSION_SPECS, _DEFAULT_DIMENSION_PRIORITY_BY_NAME, _DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME
    _DEFAULT_DIMENSION_SPECS = tuple(sorted(specs, key=lambda spec: spec.priority))
    _DEFAULT_DIMENSION_PRIORITY_BY_NAME = {spec.name: spec.priority for spec in _DEFAULT_DIMENSION_SPECS}
    _DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME = {spec.name: spec.pressure_type for spec in _DEFAULT_DIMENSION_SPECS}


def get_default_dimension_specs() -> tuple[DimensionSpec, ...]:
    """Return the currently active dimension judgment specs."""

    if not _DEFAULT_DIMENSION_SPECS:
        raise RuntimeError(
            "no dimension specs registered; activate a scenario and register its dimension specs before judgment"
        )
    return _DEFAULT_DIMENSION_SPECS



def get_default_dimension_priority_by_name() -> dict[str, int]:
    """Return the currently active dimension-priority lookup."""

    get_default_dimension_specs()
    return dict(_DEFAULT_DIMENSION_PRIORITY_BY_NAME)



def get_default_pressure_type_by_dimension_name() -> dict[str, str]:
    """Return the currently active dimension-to-pressure-type lookup."""

    get_default_dimension_specs()
    return dict(_DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME)


__all__ = [
    "DimensionSpec",
    "DimensionSnapshotFn",
    "get_default_dimension_priority_by_name",
    "get_default_dimension_specs",
    "get_default_pressure_type_by_dimension_name",
    "register_default_dimension_specs",
]
