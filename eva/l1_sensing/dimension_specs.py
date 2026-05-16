"""Scenario-owned dimension specification seam for framework judgment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from ..kernel import DimensionSnapshot, ExternalLifeConfig, emit_log_line
from .rate_sensors import RATE_SENSING_AGGREGATION_METHODS

DimensionSnapshotFn = Callable[[dict[str, object], ExternalLifeConfig], DimensionSnapshot]
RateSensingTier = Literal["required", "recommended", "optional", "unsupported_with_reason"]


@dataclass(frozen=True)
class DimensionSpec:
    """One scenario-registered dimension judgment spec."""

    name: str
    priority: int
    pressure_type: str
    snapshot_fn: DimensionSnapshotFn
    rate_sensing_tier: RateSensingTier = "optional"
    rate_sensing_reason: str | None = None
    rate_aggregation_method: str = "ewma"
    rate_window_length: int = 2
    rate_anticipatory_threshold: float | None = None


_DEFAULT_DIMENSION_SPECS: tuple[DimensionSpec, ...] = ()
_DEFAULT_DIMENSION_PRIORITY_BY_NAME: dict[str, int] = {}
_DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME: dict[str, str] = {}
_DEFAULT_DIMENSION_SPEC_BY_NAME: dict[str, DimensionSpec] = {}
_REGISTERED_PRESSURE_TYPES: tuple[str, ...] = ()

_REQUIRED_RATE_DIMENSION_HINTS = (
    "avatar_health",
    "critical_resource_missing",
    "critical_capability_missing",
    "instance_valid",
    "runtime_path_missing",
    "runtime_files_missing",
    "runtime_not_writable",
)


def _validate_dimension_specs(specs: tuple[DimensionSpec, ...]) -> None:
    """Validate one scenario's dimension-spec declarations."""

    invalid_tiers = sorted(
        spec.name
        for spec in specs
        if spec.rate_sensing_tier not in {"required", "recommended", "optional", "unsupported_with_reason"}
    )
    if invalid_tiers:
        raise ValueError("dimension specs use invalid rate_sensing_tier values: " + ", ".join(invalid_tiers))
    missing_reason = sorted(
        spec.name
        for spec in specs
        if spec.rate_sensing_tier == "unsupported_with_reason" and not (spec.rate_sensing_reason or "").strip()
    )
    if missing_reason:
        raise ValueError(
            "dimension specs declared unsupported_with_reason without rate_sensing_reason: " + ", ".join(missing_reason)
        )
    invalid_methods = sorted(
        spec.name
        for spec in specs
        if spec.rate_aggregation_method not in RATE_SENSING_AGGREGATION_METHODS
    )
    if invalid_methods:
        raise ValueError(
            "dimension specs use unsupported rate_aggregation_method values: " + ", ".join(invalid_methods)
        )
    invalid_windows = sorted(spec.name for spec in specs if spec.rate_window_length < 1)
    if invalid_windows:
        raise ValueError("dimension specs require rate_window_length >= 1: " + ", ".join(invalid_windows))
    invalid_thresholds = sorted(
        spec.name
        for spec in specs
        if spec.rate_anticipatory_threshold is not None
        and (spec.rate_sensing_tier != "required" or spec.rate_anticipatory_threshold <= 0)
    )
    if invalid_thresholds:
        raise ValueError(
            "dimension specs require positive anticipatory thresholds on required-tier dimensions only: "
            + ", ".join(invalid_thresholds)
        )



def _audit_required_rate_sensing(specs: tuple[DimensionSpec, ...]) -> None:
    """Emit a lightweight framework audit for likely failure-participating dimensions."""

    for spec in specs:
        if spec.rate_sensing_tier == "required":
            continue
        if not any(hint in spec.snapshot_fn.__code__.co_names for hint in _REQUIRED_RATE_DIMENSION_HINTS):
            continue
        emit_log_line(
            "rate_sensing_audit",
            dimension=spec.name,
            tier=spec.rate_sensing_tier,
            action="review_required_tier",
        )



def register_default_dimension_specs(
    specs: tuple[DimensionSpec, ...],
    *,
    pressure_types: tuple[str, ...] | None = None,
) -> None:
    """Register the active dimension judgment specs for the current runtime context."""

    resolved_specs = tuple(sorted(specs, key=lambda spec: spec.priority))
    resolved_pressure_types = tuple(dict.fromkeys(pressure_types or tuple(spec.pressure_type for spec in resolved_specs)))
    invalid = sorted({spec.pressure_type for spec in resolved_specs if spec.pressure_type not in resolved_pressure_types})
    if invalid:
        raise ValueError(
            "dimension specs reference unregistered pressure types: " + ", ".join(invalid)
        )
    _validate_dimension_specs(resolved_specs)
    _audit_required_rate_sensing(resolved_specs)

    global _DEFAULT_DIMENSION_SPECS, _DEFAULT_DIMENSION_PRIORITY_BY_NAME, _DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME, _DEFAULT_DIMENSION_SPEC_BY_NAME, _REGISTERED_PRESSURE_TYPES
    _DEFAULT_DIMENSION_SPECS = resolved_specs
    _REGISTERED_PRESSURE_TYPES = resolved_pressure_types
    _DEFAULT_DIMENSION_PRIORITY_BY_NAME = {spec.name: spec.priority for spec in resolved_specs}
    _DEFAULT_DIMENSION_PRESSURE_TYPE_BY_NAME = {spec.name: spec.pressure_type for spec in resolved_specs}
    _DEFAULT_DIMENSION_SPEC_BY_NAME = {spec.name: spec for spec in resolved_specs}



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



def get_default_dimension_spec_by_name() -> dict[str, DimensionSpec]:
    """Return the currently active dimension-spec lookup."""

    get_default_dimension_specs()
    return dict(_DEFAULT_DIMENSION_SPEC_BY_NAME)



def get_registered_pressure_types() -> tuple[str, ...]:
    """Return the active scenario's registered pressure-type vocabulary."""

    get_default_dimension_specs()
    return tuple(_REGISTERED_PRESSURE_TYPES)


__all__ = [
    "DimensionSpec",
    "DimensionSnapshotFn",
    "RateSensingTier",
    "get_default_dimension_priority_by_name",
    "get_default_dimension_spec_by_name",
    "get_default_dimension_specs",
    "get_default_pressure_type_by_dimension_name",
    "get_registered_pressure_types",
    "register_default_dimension_specs",
]
