"""Canonical L2 drive-state owner for deterministic update and summary logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from ..kernel import DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot
from .drive_registry import (
    DEFAULT_DRIVE_UPDATE_POLICY,
    DRIVE_TYPES,
    DRIVE_TYPE_BY_DIMENSION,
    DriveUpdatePolicy,
    severity_delta_for_status,
)

if TYPE_CHECKING:
    from ..l1_sensing.signal_bus import SignalRecord


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
    *,
    policy: DriveUpdatePolicy = DEFAULT_DRIVE_UPDATE_POLICY,
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
        drive = _update_one_drive(previous_drive, drive_type, snapshot, threat_present, policy)
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


def _update_one_drive(
    previous_drive: DriveState,
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
    policy: DriveUpdatePolicy,
) -> DriveState:
    """Apply one deterministic update step for a single drive."""

    contributors: list[str] = []
    level = previous_drive.level
    if drive_type == "curiosity":
        delta = _curiosity_delta(snapshot, threat_present, contributors, policy)
    else:
        delta = _risk_drive_delta(drive_type, snapshot, threat_present, contributors, policy)
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


def _risk_drive_delta(
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
    contributors: list[str],
    policy: DriveUpdatePolicy,
) -> float:
    """Apply named update policies for one non-curiosity drive."""

    delta = 0.0
    delta += _apply_base_decay(contributors, policy)
    delta += _apply_dimension_severity_accumulation(drive_type, snapshot, contributors, policy)
    delta += _apply_threat_bonus(threat_present, contributors, policy)
    return delta


def _apply_base_decay(contributors: list[str], policy: DriveUpdatePolicy) -> float:
    """Apply the baseline decay that gently relaxes non-curiosity drives."""

    contributors.append("decay")
    return -policy.base_decay


def _apply_dimension_severity_accumulation(
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    contributors: list[str],
    policy: DriveUpdatePolicy,
) -> float:
    """Accumulate judged dimension severity onto the mapped drive."""

    delta = 0.0
    for dimension_name, dimension in snapshot.dimensions.items():
        if DRIVE_TYPE_BY_DIMENSION.get(dimension_name) != drive_type:
            continue
        severity_delta = severity_delta_for_status(dimension.status, policy)
        if severity_delta <= 0:
            continue
        delta += severity_delta
        contributors.append(f"{dimension_name}.{_reason(dimension)}")
    return delta


def _apply_threat_bonus(threat_present: bool, contributors: list[str], policy: DriveUpdatePolicy) -> float:
    """Apply the additional threat bonus when the patrol emitted threat signals."""

    if not threat_present:
        return 0.0
    contributors.append("threat_signal_present")
    return policy.threat_bonus


def _curiosity_delta(
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
    contributors: list[str],
    policy: DriveUpdatePolicy,
) -> float:
    """Update curiosity through explicit recovery or suppression semantics."""

    suppression = _curiosity_suppression_delta(snapshot, threat_present, contributors, policy)
    if suppression != 0.0:
        return suppression
    return _curiosity_recovery_delta(contributors, policy)


def _curiosity_suppression_delta(
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
    contributors: list[str],
    policy: DriveUpdatePolicy,
) -> float:
    """Suppress curiosity under threat or degraded overall conditions."""

    if threat_present:
        contributors.append("threat_suppression")
        return -policy.curiosity_suppression
    if snapshot.overall_status in {"degraded", "critical"}:
        contributors.append(f"overall_status.{snapshot.overall_status}")
        return -policy.curiosity_suppression
    return 0.0


def _curiosity_recovery_delta(contributors: list[str], policy: DriveUpdatePolicy) -> float:
    """Recover curiosity when the patrol result is healthy and threat-free."""

    contributors.append("healthy_recovery")
    return policy.curiosity_recovery


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


__all__ = [
    "DriveSummary",
    "build_default_drive_state",
    "summarize_drive_state",
    "update_drive_state",
]
