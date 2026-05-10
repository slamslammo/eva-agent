"""Linux runtime drive preset retained under scenario ownership for Phase A."""

from __future__ import annotations

from eva.l2_drive.drive_registry import DrivePreset, DriveUpdatePolicy

DRIVE_TYPES = ("survival", "integrity", "continuity", "curiosity")
DRIVE_TYPE_BY_DIMENSION = {
    "resource_state": "survival",
    "runtime_integrity": "integrity",
    "anomaly_accumulation": "integrity",
    "host_continuity": "continuity",
}
DEFAULT_DRIVE_UPDATE_POLICY = DriveUpdatePolicy()
LINUX_RUNTIME_DRIVE_PRESET = DrivePreset(
    drive_types=DRIVE_TYPES,
    drive_type_by_dimension=DRIVE_TYPE_BY_DIMENSION,
    default_policy=DEFAULT_DRIVE_UPDATE_POLICY,
    curiosity_drive_type="curiosity",
)

__all__ = [
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
    "LINUX_RUNTIME_DRIVE_PRESET",
]
