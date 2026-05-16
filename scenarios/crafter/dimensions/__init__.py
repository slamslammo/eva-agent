"""Crafter dimension-spec surfaces for Stage H H-0F."""

from __future__ import annotations

from eva.l1_sensing.dimension_specs import DimensionSpec

from .judgment import (
    avatar_metabolic_snapshot,
    avatar_recovery_snapshot,
    avatar_safety_snapshot,
    inventory_acquisition_snapshot,
    inventory_capability_snapshot,
    local_view_resource_snapshot,
    local_view_threat_snapshot,
    local_view_utility_snapshot,
)

CRAFTER_DIMENSION_SPECS = (
    DimensionSpec(
        name="avatar_safety",
        priority=0,
        pressure_type="safety",
        snapshot_fn=avatar_safety_snapshot,
        rate_sensing_tier="required",
        rate_aggregation_method="ewma",
        rate_window_length=2,
        rate_anticipatory_threshold=0.12,
    ),
    DimensionSpec(
        name="avatar_metabolic",
        priority=1,
        pressure_type="metabolic",
        snapshot_fn=avatar_metabolic_snapshot,
        rate_sensing_tier="required",
        rate_aggregation_method="ewma",
        rate_window_length=2,
        rate_anticipatory_threshold=0.12,
    ),
    DimensionSpec(
        name="avatar_recovery",
        priority=2,
        pressure_type="recovery",
        snapshot_fn=avatar_recovery_snapshot,
        rate_sensing_tier="required",
        rate_aggregation_method="ewma",
        rate_window_length=2,
    ),
    DimensionSpec(
        name="inventory_capability",
        priority=3,
        pressure_type="capability",
        snapshot_fn=inventory_capability_snapshot,
        rate_sensing_tier="recommended",
        rate_aggregation_method="ewma",
        rate_window_length=2,
    ),
    DimensionSpec(
        name="inventory_acquisition",
        priority=4,
        pressure_type="acquisition",
        snapshot_fn=inventory_acquisition_snapshot,
        rate_sensing_tier="recommended",
        rate_aggregation_method="ewma",
        rate_window_length=2,
    ),
    DimensionSpec(
        name="local_view_threat",
        priority=5,
        pressure_type="safety",
        snapshot_fn=local_view_threat_snapshot,
        rate_sensing_tier="optional",
        rate_aggregation_method="first_order_diff",
        rate_window_length=2,
    ),
    DimensionSpec(
        name="local_view_resource",
        priority=6,
        pressure_type="acquisition",
        snapshot_fn=local_view_resource_snapshot,
        rate_sensing_tier="optional",
        rate_aggregation_method="first_order_diff",
        rate_window_length=2,
    ),
    DimensionSpec(
        name="local_view_utility",
        priority=7,
        pressure_type="capability",
        snapshot_fn=local_view_utility_snapshot,
        rate_sensing_tier="optional",
        rate_aggregation_method="first_order_diff",
        rate_window_length=2,
    ),
)

__all__ = ["CRAFTER_DIMENSION_SPECS"]
