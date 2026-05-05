"""Canonical L2 drive registry constants and explicit update policy surfaces."""

from __future__ import annotations

from dataclasses import dataclass

DRIVE_TYPES = ("survival", "integrity", "continuity", "curiosity")
DRIVE_TYPE_BY_DIMENSION = {
    "resource_state": "survival",
    "runtime_integrity": "integrity",
    "anomaly_accumulation": "integrity",
    "host_continuity": "continuity",
}


@dataclass(frozen=True)
class DriveUpdatePolicy:
    """Explicit parameter surface for one L2 drive reconciliation step."""

    base_decay: float = 0.05
    severity_degraded_delta: float = 0.18
    severity_critical_delta: float = 0.36
    threat_bonus: float = 0.04
    curiosity_recovery: float = 0.08
    curiosity_suppression: float = 0.12


DEFAULT_DRIVE_UPDATE_POLICY = DriveUpdatePolicy()


def severity_delta_for_status(status: str, policy: DriveUpdatePolicy) -> float:
    """Return the configured severity accumulation for one judged status."""

    if status == "critical":
        return policy.severity_critical_delta
    if status == "degraded":
        return policy.severity_degraded_delta
    return 0.0


__all__ = [
    "DEFAULT_DRIVE_UPDATE_POLICY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
    "DriveUpdatePolicy",
    "severity_delta_for_status",
]
