"""Crafter drive preset (Stage H H-1 + Round 1.B-2 exploration drive)."""

from __future__ import annotations

from eva.l2_drive.drive_registry import DrivePreset, DriveUpdatePolicy

# Round 1.B-2: ``exploration`` joins the Crafter drive family as the
# scenario's growth-driver pull (v0.6.1 §4). It is an *internal* drive — it is
# NOT mapped to any sensor dimension. Instead it is updated through the
# framework's curiosity-style ``_curiosity_delta`` recovery / suppression path:
# rises in healthy / no-threat states, falls under threat or degraded
# overall status. Candidate scoring picks up this drive via
# ``COMPATIBILITY_RELEASE_IMPACT`` per profile (see scenarios/crafter/anchors/policy.py).
DRIVE_TYPES = (
    "metabolic",
    "safety",
    "recovery",
    "acquisition",
    "capability",
    "exploration",
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
    # ``exploration`` is intentionally absent from this mapping — it is not
    # driven by any sensor signal. The curiosity-style update path handles it.
}

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
    # Round 1.B-2: opt into the framework curiosity-style update path for the
    # exploration drive (previously Crafter set this to None, dead-coding the
    # path).
    curiosity_drive_type="exploration",
)

__all__ = [
    "CRAFTER_DRIVE_PRESET",
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
]
