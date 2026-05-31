"""Linux runtime drive preset — identity derived from the single LINUX_DRIVE_SPEC.

single-source-linux-drive-metadata (A G1 §10): Linux is rule-driven (no dlPFC,
no drive ontology), so it adopts ScenarioDriveSpec for ONLY the engine identity
fields (drive_types / dimension-map / curiosity) — an engine-only spec with no
LLM semantic text. DriveUpdatePolicy stays authored here (behavior, not identity),
mirroring the Crafter single-source split. Linux never builds a drive ontology
(the framework guard refuses an empty-semantics ontology).
"""

from __future__ import annotations

from eva.l2_drive.drive_registry import DrivePreset, DriveUpdatePolicy
from eva.l3_deliberation.ontology import DriveSpecEntry, ScenarioDriveSpec

# Engine-only single source: identity fields only (no meaning/low/high — Linux
# has no dlPFC ontology). ``integrity`` is fed by two sensor dimensions.
LINUX_DRIVE_SPEC = ScenarioDriveSpec(
    version="linux-drive-spec-v1",
    entries=(
        DriveSpecEntry(name="survival", dimensions=("resource_state",)),
        DriveSpecEntry(
            name="integrity",
            dimensions=("runtime_integrity", "anomaly_accumulation"),
        ),
        DriveSpecEntry(name="continuity", dimensions=("host_continuity",)),
        DriveSpecEntry(name="curiosity", is_curiosity=True),
    ),
)

DRIVE_TYPES = LINUX_DRIVE_SPEC.drive_types()
DRIVE_TYPE_BY_DIMENSION = LINUX_DRIVE_SPEC.drive_type_by_dimension()
DEFAULT_DRIVE_UPDATE_POLICY = DriveUpdatePolicy()
LINUX_RUNTIME_DRIVE_PRESET = DrivePreset(
    drive_types=DRIVE_TYPES,
    drive_type_by_dimension=DRIVE_TYPE_BY_DIMENSION,
    default_policy=DEFAULT_DRIVE_UPDATE_POLICY,
    curiosity_drive_type=LINUX_DRIVE_SPEC.curiosity_drive_type(),
)

__all__ = [
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
    "LINUX_DRIVE_SPEC",
    "LINUX_RUNTIME_DRIVE_PRESET",
]
