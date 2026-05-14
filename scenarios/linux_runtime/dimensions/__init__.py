"""Linux runtime dimension-spec surfaces for H-0F."""

from __future__ import annotations

from eva.l1_sensing.dimension_specs import DimensionSpec

from .judgment import (
    anomaly_accumulation_snapshot,
    host_continuity_snapshot,
    resource_state_snapshot,
    runtime_integrity_snapshot,
)

LINUX_RUNTIME_DIMENSION_SPECS = (
    DimensionSpec(name="runtime_integrity", priority=0, pressure_type="integrity", snapshot_fn=runtime_integrity_snapshot),
    DimensionSpec(name="host_continuity", priority=1, pressure_type="continuity", snapshot_fn=host_continuity_snapshot),
    DimensionSpec(name="resource_state", priority=2, pressure_type="resource_state", snapshot_fn=resource_state_snapshot),
    DimensionSpec(name="anomaly_accumulation", priority=3, pressure_type="anomaly_accumulation", snapshot_fn=anomaly_accumulation_snapshot),
)

__all__ = ["LINUX_RUNTIME_DIMENSION_SPECS"]
