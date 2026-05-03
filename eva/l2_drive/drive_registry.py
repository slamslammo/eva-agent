"""Canonical L2 drive registry constants and dimension mappings."""

from __future__ import annotations

DRIVE_TYPES = ("survival", "integrity", "continuity", "curiosity")
DRIVE_TYPE_BY_DIMENSION = {
    "resource_state": "survival",
    "runtime_integrity": "integrity",
    "anomaly_accumulation": "integrity",
    "host_continuity": "continuity",
}
SEVERITY_DELTA = {
    "healthy": 0.0,
    "degraded": 0.18,
    "critical": 0.36,
}
BASE_DECAY = 0.05
CURIOSITY_RECOVERY = 0.08
THREAT_SUPPRESSION = 0.12

__all__ = [
    "BASE_DECAY",
    "CURIOSITY_RECOVERY",
    "DRIVE_TYPES",
    "DRIVE_TYPE_BY_DIMENSION",
    "SEVERITY_DELTA",
    "THREAT_SUPPRESSION",
]
