"""Crafter dimension-spec surfaces for Stage H H-0F."""

from __future__ import annotations

from eva.l1_sensing.dimension_specs import DimensionSpec

from .judgment import (
    avatar_metabolic_snapshot,
    avatar_recovery_snapshot,
    avatar_safety_snapshot,
    inventory_acquisition_snapshot,
    inventory_capability_snapshot,
    local_view_state_snapshot,
)

CRAFTER_DIMENSION_SPECS = (
    DimensionSpec(name="avatar_safety", priority=0, pressure_type="integrity", snapshot_fn=avatar_safety_snapshot),
    DimensionSpec(name="avatar_metabolic", priority=1, pressure_type="integrity", snapshot_fn=avatar_metabolic_snapshot),
    DimensionSpec(name="avatar_recovery", priority=2, pressure_type="integrity", snapshot_fn=avatar_recovery_snapshot),
    DimensionSpec(name="inventory_capability", priority=3, pressure_type="integrity", snapshot_fn=inventory_capability_snapshot),
    DimensionSpec(name="inventory_acquisition", priority=4, pressure_type="integrity", snapshot_fn=inventory_acquisition_snapshot),
    DimensionSpec(name="local_view_state", priority=5, pressure_type="integrity", snapshot_fn=local_view_state_snapshot),
)

__all__ = ["CRAFTER_DIMENSION_SPECS"]
