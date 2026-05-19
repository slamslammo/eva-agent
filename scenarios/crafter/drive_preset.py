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
    # Round 1.B-2 → Phase-1.5 → Round 1.B-4 → Fix-1 tuning history:
    #
    # Original Round 1.B-2 used Linux defaults (0.05 / 0.12). Phase-1.5
    # bumped recovery to 0.10 and dropped suppression to 0.06, AND set
    # ``curiosity_suppress_on_degraded_status=False``, on the theory that
    # the framework was over-suppressing. Round 1.B-4 then found the
    # actual root cause was in the signal-classification layer (all
    # active pressures emitting class="threat"). With 1.B-4 in place the
    # Phase-1.5 recovery/suppression numbers over-corrected: exploration
    # drive saturated near 1.0 within 10 ticks because Crafter rarely
    # surfaces real safety threats once the spurious threat signals are
    # gone. Fix-1 reverts the numeric tuning to Linux defaults
    # (0.05 / 0.12) while keeping the ``suppress_on_degraded=False`` flag
    # — the latter is still principled (avatar persistently degraded
    # shouldn't drive curiosity to 0) and is independent of signal-class
    # semantics. Re-tune via long-run trajectory data.
    curiosity_recovery=0.05,
    curiosity_suppression=0.12,
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
