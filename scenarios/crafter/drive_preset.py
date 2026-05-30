"""Crafter drive preset (Stage H H-1 + Round 1.B-2 exploration drive)."""

from __future__ import annotations

from eva.l2_drive.drive_registry import DrivePreset, DriveUpdatePolicy

from .drive_spec import CRAFTER_DRIVE_SPEC

# single-source-scenario-drive-metadata: drive identity (types / dimension map /
# curiosity drive) is now DERIVED from CRAFTER_DRIVE_SPEC, the single authority
# source it shares with CRAFTER_DRIVE_ONTOLOGY. This removes the prior drift risk
# between this preset and the drive ontology text. DriveUpdatePolicy below is
# behavior tuning and stays authored here (not part of the spec).
#
# Round 1.B-2 (carried over): ``exploration`` is an *internal* drive — declared
# in the spec with empty ``dimensions`` so it is absent from
# DRIVE_TYPE_BY_DIMENSION, and ``is_curiosity=True`` so it becomes
# curiosity_drive_type. It is updated through the framework's curiosity-style
# ``_curiosity_delta`` recovery / suppression path; candidate scoring picks it up
# via ``COMPATIBILITY_RELEASE_IMPACT`` per profile (see
# scenarios/crafter/anchors/policy.py).
DRIVE_TYPES = CRAFTER_DRIVE_SPEC.drive_types()

DRIVE_TYPE_BY_DIMENSION = CRAFTER_DRIVE_SPEC.drive_type_by_dimension()

DEFAULT_DRIVE_UPDATE_POLICY = DriveUpdatePolicy(
    # Fix-C: Crafter opts into approach-mode drive updates — each risk drive moves
    # toward a severity target (critical→0.9 / degraded→0.55 / healthy→0) instead
    # of accumulating linearly to 1.0. Under Crafter's "everything is scarce"
    # opening this keeps drives layered so drive-impact scoring still discriminates
    # which need is most urgent (linear accumulate pinned every drive at 1.0).
    update_mode="approach",
    approach_rate=0.3,
    target_critical=0.9,
    target_degraded=0.55,
    # Accumulate-mode params below are unused under approach mode (kept for revert;
    # see git history for the Round 1.B-2 → Phase-1.5 → 1.B-4 → Fix-1 tuning notes).
    base_decay=0.04,
    severity_degraded_delta=0.16,
    severity_critical_delta=0.32,
    threat_bonus=0.08,
    # Curiosity still uses recovery/suppression (independent of approach mode);
    # Fix-C lowers suppression / raises recovery so persistent threat signals
    # don't pin exploration drive at 0.
    curiosity_recovery=0.07,
    curiosity_suppression=0.06,
    curiosity_suppress_on_degraded_status=False,
)

CRAFTER_DRIVE_PRESET = DrivePreset(
    drive_types=DRIVE_TYPES,
    drive_type_by_dimension=DRIVE_TYPE_BY_DIMENSION,
    default_policy=DEFAULT_DRIVE_UPDATE_POLICY,
    # Derived from the spec: opt into the framework curiosity-style update path
    # for the exploration drive (the single is_curiosity=True entry).
    curiosity_drive_type=CRAFTER_DRIVE_SPEC.curiosity_drive_type(),
)

__all__ = [
    "CRAFTER_DRIVE_PRESET",
    "CRAFTER_DRIVE_SPEC",
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
]
