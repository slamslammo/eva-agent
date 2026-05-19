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
    base_decay=0.04,
    severity_degraded_delta=0.16,
    severity_critical_delta=0.32,
    threat_bonus=0.08,
    # Round 1.B-2 → Phase-1.5 tuning (post-10min validation):
    # Linux defaults (0.05 / 0.12) produce exploration drive level == 0
    # across all 96 turns of a 10min Crafter run because the framework's
    # curiosity-suppression branch fires on EVERY degraded/critical
    # overall_status — and the Crafter avatar's food/water/energy keep it
    # in degraded territory almost continuously. Recovery doubled and
    # suppression halved, but more importantly the
    # ``curiosity_suppress_on_degraded_status`` flag is OFF so suppression
    # fires only on actual threat signals, leaving sustained sub-critical
    # avatar pressure as a window where exploration drive can accumulate.
    # Re-tune via Round 1.D long-run data.
    curiosity_recovery=0.10,
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
