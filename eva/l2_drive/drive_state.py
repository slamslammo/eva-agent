"""Canonical L2 drive-state owner for deterministic update and summary logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from ..kernel import DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot
from .drive_registry import (
    DrivePreset,
    DriveUpdatePolicy,
    get_default_drive_preset,
    severity_delta_for_status,
    severity_target_for_status,
)
from ..observability import current_trace_sink, current_trace_turn_index

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


def build_default_drive_state(
    captured_at: datetime,
    *,
    preset: DrivePreset | None = None,
) -> DriveStateTable:
    """Build the default drive table for the active scenario preset."""

    resolved_preset = preset or get_default_drive_preset()
    return DriveStateTable(
        captured_at=captured_at,
        drives=[DriveState(drive_type=drive_type, updated_at=captured_at) for drive_type in resolved_preset.drive_types],
        updated_at=captured_at,
    )


def update_drive_state(
    previous: DriveStateTable | None,
    snapshot: ExternalLifeSnapshot,
    signals: Iterable[SignalRecord],
    *,
    policy: DriveUpdatePolicy | None = None,
    preset: DrivePreset | None = None,
) -> tuple[DriveStateTable, DriveSummary]:
    """Update the continuous drive table from the latest patrol snapshot and signal batch."""

    resolved_preset = preset or get_default_drive_preset()
    resolved_policy = policy or resolved_preset.default_policy
    previous_table = previous or build_default_drive_state(snapshot.captured_at, preset=resolved_preset)
    previous_by_type = {drive.drive_type: drive for drive in previous_table.drives}
    signal_list = list(signals)
    threat_present = any(signal.signal_class == "threat" for signal in signal_list)
    updated_drives: list[DriveState] = []
    changed_drives: list[str] = []

    for drive_type in resolved_preset.drive_types:
        previous_drive = previous_by_type.get(drive_type, DriveState(drive_type=drive_type, updated_at=snapshot.captured_at))
        drive = _update_one_drive(previous_drive, drive_type, snapshot, threat_present, resolved_preset, resolved_policy)
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
    top_drive = drives_by_level[0] if drives_by_level else DriveState(drive_type="unknown", level=0.0)
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
    preset: DrivePreset,
    policy: DriveUpdatePolicy,
) -> DriveState:
    """Apply one deterministic update step for a single drive."""

    contributors: list[str] = []
    level = previous_drive.level
    if preset.is_curiosity_drive(drive_type):
        delta = _curiosity_delta(snapshot, threat_present, contributors, policy)
    else:
        delta = _risk_drive_delta(drive_type, snapshot, threat_present, contributors, preset, policy, level=level)
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
    preset: DrivePreset,
    policy: DriveUpdatePolicy,
    *,
    level: float,
) -> float:
    """Apply named update policies for one non-curiosity drive."""

    if policy.update_mode == "approach":
        return _approach_target_delta(drive_type, snapshot, threat_present, contributors, preset, policy, level)
    delta = 0.0
    delta += _apply_base_decay(contributors, policy)
    delta += _apply_dimension_severity_accumulation(drive_type, snapshot, contributors, preset, policy)
    delta += _apply_threat_bonus(threat_present, contributors, policy)
    return delta


def _approach_target_delta(
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    threat_present: bool,
    contributors: list[str],
    preset: DrivePreset,
    policy: DriveUpdatePolicy,
    level: float,
) -> float:
    """Fix-C: move one drive toward the worst severity-derived target.

    The target is the highest among the drive's mapped dimensions (critical→
    target_critical, degraded→target_degraded, healthy→0); a present threat
    lifts it to at least target_degraded. The drive then moves a fraction
    ``approach_rate`` of the gap, so sustained critical settles near
    target_critical (not 1.0) and recovered dimensions decay back toward 0.
    """

    target = 0.0
    for dimension_name, dimension in snapshot.dimensions.items():
        if preset.drive_for_dimension(dimension_name) != drive_type:
            continue
        dimension_target = severity_target_for_status(dimension.status, policy)
        if dimension_target > target:
            target = dimension_target
            contributors.append(f"{dimension_name}.{_reason(dimension)}")
    if threat_present and target < policy.target_degraded:
        target = policy.target_degraded
        contributors.append("threat_signal_present")
    if not contributors:
        contributors.append("approach_target")
    result = policy.approach_rate * (target - level)
    # Round 1.H H-2c: flag-gated read-only owner-hook (A-approved exception #1).
    # The per-drive target / approach_rate / contributor reasons are local here and
    # invisible at any seam. Emission is gated on the process-current trace sink
    # (NullTraceSink when EVA_TRACE is off → no-op → byte-equivalent); it never
    # touches the return value or control flow.
    _trace = current_trace_sink()
    if _trace.enabled:
        _trace.emit_transform(
            layer="L2",
            transform_id="l2.approach_delta",
            code_anchor="eva/l2_drive/drive_state.py:_approach_target_delta",
            turn_index=current_trace_turn_index(),
            inputs={"drive_type": drive_type, "level": level, "threat_present": threat_present},
            outputs={
                "target": target,
                "delta": result,
                "approach_rate": policy.approach_rate,
                "contributors": list(contributors),
            },
        )
    return result


def _apply_base_decay(contributors: list[str], policy: DriveUpdatePolicy) -> float:
    """Apply the baseline decay that gently relaxes non-curiosity drives."""

    contributors.append("decay")
    return -policy.base_decay


def _apply_dimension_severity_accumulation(
    drive_type: str,
    snapshot: ExternalLifeSnapshot,
    contributors: list[str],
    preset: DrivePreset,
    policy: DriveUpdatePolicy,
) -> float:
    """Accumulate judged dimension severity onto the mapped drive."""

    delta = 0.0
    for dimension_name, dimension in snapshot.dimensions.items():
        if preset.drive_for_dimension(dimension_name) != drive_type:
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
    """Suppress curiosity under threat or degraded overall conditions.

    Phase-1.5: the degraded/critical overall_status check is gated by
    ``policy.curiosity_suppress_on_degraded_status`` (default True for
    Linux equivalence). Scenarios where the avatar is in a persistently
    degraded state (e.g. Crafter) can opt out via the policy flag so
    exploration drive can accumulate during sub-critical sustained
    pressure rather than being pinned at 0.
    """

    if threat_present:
        contributors.append("threat_suppression")
        return -policy.curiosity_suppression
    if policy.curiosity_suppress_on_degraded_status and snapshot.overall_status in {"degraded", "critical"}:
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
