"""Crafter drive preset for Stage H H-1."""

from __future__ import annotations

from eva.l2_drive.drive_registry import DrivePreset, DriveUpdatePolicy

DRIVE_TYPES = (
    "metabolic",
    "safety",
    "recovery",
    "acquisition",
    "capability",
)

DRIVE_TYPE_BY_DIMENSION = {
    "avatar_metabolic": "metabolic",
    "avatar_safety": "safety",
    "avatar_recovery": "recovery",
    "inventory_acquisition": "acquisition",
    "inventory_capability": "capability",
    "local_view_threat": "safety",
    "local_view_resource": "acquisition",
    "local_view_utility": "capability",
}

DEFAULT_DRIVE_UPDATE_POLICY = DriveUpdatePolicy(
    base_decay=0.04,
    severity_degraded_delta=0.16,
    severity_critical_delta=0.32,
    threat_bonus=0.08,
    curiosity_recovery=0.0,
    curiosity_suppression=0.0,
)

CRAFTER_DRIVE_PRESET = DrivePreset(
    drive_types=DRIVE_TYPES,
    drive_type_by_dimension=DRIVE_TYPE_BY_DIMENSION,
    default_policy=DEFAULT_DRIVE_UPDATE_POLICY,
    curiosity_drive_type=None,
)

__all__ = [
    "CRAFTER_DRIVE_PRESET",
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
]
