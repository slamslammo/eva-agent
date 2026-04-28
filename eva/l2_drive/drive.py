"""Continuous L2 drive state and deterministic patrol-based update rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from ..kernel import DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot, to_iso8601
from ..l1_sensing.signal_bus import SignalRecord

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


@dataclass(frozen=True)
class DriveSummary:
    """Compact patrol-facing summary of the current drive table."""

    top_drive: str
    top_level: float
    changed_drives: list[str]
    drive_levels: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Serialize the compact summary for turn details."""

        return {
            "top_drive": self.top_drive,
            "top_level": self.top_level,
            "changed_drives": list(self.changed_drives),
            "drive_levels": dict(self.drive_levels),
        }


@dataclass(frozen=True)
class DriveBroadcast:
    """Canonical read-only L2 broadcast projection for downstream consumers."""

    captured_at: str | None
    updated_at: str | None
    top_drive: str
    top_level: float
    drive_levels: dict[str, float]
    drive_trends: dict[str, str]
    drives: dict[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Serialize the read-only broadcast view for downstream consumers."""

        return {
            "captured_at": self.captured_at,
            "updated_at": self.updated_at,
            "top_drive": self.top_drive,
            "top_level": self.top_level,
            "drive_levels": dict(self.drive_levels),
            "drive_trends": dict(self.drive_trends),
            "drives": {drive_type: dict(payload) for drive_type, payload in self.drives.items()},
        }


def build_default_drive_state(captured_at: datetime) -> DriveStateTable:
    """Build the default Phase A drive table with all four drives present."""

    return DriveStateTable(
        captured_at=captured_at,
        drives=[DriveState(drive_type=drive_type, updated_at=captured_at) for drive_type in DRIVE_TYPES],
        updated_at=captured_at,
    )


def update_drive_state(
    previous: DriveStateTable | None,
    snapshot: ExternalLifeSnapshot,
    signals: Iterable[SignalRecord],
) -> tuple[DriveStateTable, DriveSummary]:
    """Update the continuous drive table from the latest patrol snapshot and signal batch."""

    previous_table = previous or build_default_drive_state(snapshot.captured_at)
    previous_by_type = {drive.drive_type: drive for drive in previous_table.drives}
    signal_list = list(signals)
    threat_present = any(signal.signal_class == "threat" for signal in signal_list)
    updated_drives: list[DriveState] = []
    changed_drives: list[str] = []

    for drive_type in DRIVE_TYPES:
        previous_drive = previous_by_type.get(drive_type, DriveState(drive_type=drive_type, updated_at=snapshot.captured_at))
        drive = _update_one_drive(previous_drive, drive_type, snapshot, threat_present)
        updated_drives.append(drive)
        if abs(drive.delta) > 1e-9:
            changed_drives.append(drive_type)

    table = DriveStateTable(
        captured_at=snapshot.captured_at,
        drives=updated_drives,
        updated_at=snapshot.updated_at,
    )
    summary = summarize_drive_state(table, changed_drives=changed_drives)
    return table, summary


def summarize_drive_state(table: DriveStateTable, *, changed_drives: list[str] | None = None) -> DriveSummary:
    """Summarize the latest drive state for patrol/lifecycle visibility."""

    drives_by_level = sorted(table.drives, key=lambda drive: (-drive.level, drive.drive_type))
    top_drive = drives_by_level[0] if drives_by_level else DriveState(drive_type="survival", level=0.0)
    return DriveSummary(
        top_drive=top_drive.drive_type,
        top_level=top_drive.level,
        changed_drives=list(changed_drives or []),
        drive_levels={drive.drive_type: drive.level for drive in table.drives},
    )


def build_drive_broadcast(table: DriveStateTable) -> DriveBroadcast:
    """Project the current drive table into the public read-only L2 broadcast view."""

    summary = summarize_drive_state(table)
    return DriveBroadcast(
        captured_at=to_iso8601(table.captured_at),
        updated_at=to_iso8601(table.updated_at),
        top_drive=summary.top_drive,
        top_level=summary.top_level,
        drive_levels=dict(summary.drive_levels),
        drive_trends={drive.drive_type: drive.trend for drive in table.drives},
        drives={
            drive.drive_type: {
                "level": drive.level,
                "delta": drive.delta,
                "trend": drive.trend,
                "contributors": list(drive.contributors),
                "updated_at": to_iso8601(drive.updated_at),
            }
            for drive in table.drives
        },
    )


def _update_one_drive(
    previous_drive: DriveState,
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
) -> DriveState:
    """Apply one deterministic update step for a single drive."""

    contributors: list[str] = []
    level = previous_drive.level
    if drive_type == "curiosity":
        delta = _curiosity_delta(snapshot, threat_present, contributors)
    else:
        delta = -BASE_DECAY
        contributors.append("decay")
        for dimension_name, dimension in snapshot.dimensions.items():
            if DRIVE_TYPE_BY_DIMENSION.get(dimension_name) != drive_type:
                continue
            severity_delta = SEVERITY_DELTA.get(dimension.status, 0.0)
            if severity_delta <= 0:
                continue
            delta += severity_delta
            contributors.append(f"{dimension_name}.{_reason(dimension)}")
        if threat_present:
            delta += 0.04
            contributors.append("threat_signal_present")
    new_level = _clamp(level + delta)
    actual_delta = new_level - level
    return DriveState(
        drive_type=drive_type,
        level=new_level,
        delta=actual_delta,
        trend=_trend_from_delta(actual_delta),
        contributors=_normalized_contributors(contributors, actual_delta),
        updated_at=snapshot.updated_at,
    )


def _curiosity_delta(snapshot: ExternalLifeSnapshot, threat_present: bool, contributors: list[str]) -> float:
    """Update curiosity as a recovery-oriented drive suppressed by threat."""

    if threat_present or snapshot.overall_status in {"degraded", "critical"}:
        contributors.extend(["threat_suppression"] if threat_present else [f"overall_status.{snapshot.overall_status}"])
        return -THREAT_SUPPRESSION
    contributors.append("healthy_recovery")
    return CURIOSITY_RECOVERY


def _reason(dimension: DimensionSnapshot) -> str:
    """Extract the compact reason string from one judged dimension."""

    return str(dimension.evidence.get("reason") or dimension.status)


def _trend_from_delta(delta: float) -> str:
    """Translate one continuous delta into a compact trend label."""

    if delta > 0:
        return "worsening"
    if delta < 0:
        return "improving"
    return "stable"


def _clamp(value: float) -> float:
    """Clamp one drive level into the Phase A range."""

    return max(0.0, min(1.0, round(value, 4)))


def _normalized_contributors(contributors: list[str], delta: float) -> list[str]:
    """Remove duplicates and keep a stable contributor order."""

    if abs(delta) <= 1e-9:
        return []
    ordered: list[str] = []
    for contributor in contributors:
        if contributor not in ordered:
            ordered.append(contributor)
    return ordered
