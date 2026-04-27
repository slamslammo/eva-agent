"""Write patrol results into current-state files and append-only survival history."""

from __future__ import annotations

from typing import Any

from ..kernel import ActivePressure, ActivePressureTable, ExternalLifeSnapshot, StateStore, to_iso8601


def _build_summary(snapshot: ExternalLifeSnapshot) -> str:
    """Build a short human-readable summary for survival history entries."""

    gap_type = str(snapshot.primary_gap.get("type") or "none")
    gap_reason = str(snapshot.primary_gap.get("reason") or "none")
    if gap_type == "none":
        return f"overall status is {snapshot.overall_status}"
    return f"{gap_type} is {gap_reason} while overall status is {snapshot.overall_status}"


def build_survival_snapshot_entry(snapshot: ExternalLifeSnapshot, pressure_table: ActivePressureTable) -> dict[str, Any]:
    """Build an append-only history entry for a full survival snapshot."""

    return {
        "event_type": "survival_snapshot",
        "timestamp": to_iso8601(snapshot.captured_at),
        "source_patrol": snapshot.source_patrol,
        "overall_status": snapshot.overall_status,
        "primary_gap": snapshot.primary_gap,
        "trend": snapshot.trend,
        "active_pressure_ids": [pressure.pressure_id for pressure in pressure_table.pressures],
        "details": {
            "dimension_status": {
                key: value.status for key, value in snapshot.dimensions.items()
            },
            "summary": _build_summary(snapshot),
        },
    }


def build_pressure_event(
    event_type: str,
    pressure: ActivePressure,
    snapshot: ExternalLifeSnapshot,
) -> dict[str, Any]:
    """Build an append-only history entry for a pressure open/resolve event."""

    return {
        "event_type": event_type,
        "timestamp": to_iso8601(snapshot.captured_at),
        "source_patrol": snapshot.source_patrol,
        "overall_status": snapshot.overall_status,
        "primary_gap": snapshot.primary_gap,
        "trend": snapshot.trend,
        "pressure_id": pressure.pressure_id,
        "details": {
            "type": pressure.type,
            "severity": pressure.severity,
            "trend": pressure.trend,
            "evidence": pressure.evidence,
            "first_seen_at": to_iso8601(pressure.first_seen_at),
            "last_seen_at": to_iso8601(pressure.last_seen_at),
        },
    }


def persist_patrol_artifacts(
    store: StateStore,
    snapshot: ExternalLifeSnapshot,
    pressure_table: ActivePressureTable,
    *,
    opened_pressures: list[ActivePressure],
    resolved_pressures: list[ActivePressure],
    append_snapshot: bool,
) -> None:
    """Persist current patrol outputs and append the relevant history entries."""

    store.write_external_life_snapshot(snapshot)
    store.write_active_pressures(pressure_table)
    for pressure in opened_pressures:
        store.append_survival_log(build_pressure_event("pressure_opened", pressure, snapshot))
    for pressure in resolved_pressures:
        store.append_survival_log(build_pressure_event("pressure_resolved", pressure, snapshot))
    if append_snapshot:
        store.append_survival_log(build_survival_snapshot_entry(snapshot, pressure_table))
