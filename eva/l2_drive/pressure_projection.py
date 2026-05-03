"""Readonly compatibility pressure projection from judged gaps."""

from __future__ import annotations

import re

from ..kernel import ActivePressure, ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot

SEVERITY_ORDER = {"healthy": 0, "degraded": 1, "critical": 2}
PRESSURE_TYPE_BY_DIMENSION = {
    "host_continuity": "continuity",
    "runtime_integrity": "integrity",
    "resource_state": "resource_state",
    "anomaly_accumulation": "anomaly_accumulation",
}


def project_active_pressures(
    snapshot: ExternalLifeSnapshot,
    previous_table: ActivePressureTable,
) -> list[ActivePressure]:
    """Project non-healthy judged gaps into compatibility pressure records."""

    previous_by_id = {pressure.pressure_id: pressure for pressure in previous_table.pressures}
    current_pressures: list[ActivePressure] = []
    for dimension_name, dimension in snapshot.dimensions.items():
        if dimension.status == "healthy":
            continue
        pressure_type = PRESSURE_TYPE_BY_DIMENSION[dimension_name]
        pressure_id = _build_pressure_id(pressure_type, dimension)
        previous = previous_by_id.get(pressure_id)
        current_pressures.append(
            ActivePressure(
                pressure_id=pressure_id,
                type=pressure_type,
                severity=dimension.status,
                evidence=dict(dimension.evidence),
                first_seen_at=snapshot.captured_at if previous is None else previous.first_seen_at,
                last_seen_at=snapshot.captured_at,
                trend=_pressure_trend(dimension.status, previous),
                active=True,
            )
        )
    return current_pressures


def _normalize_reason(value: str) -> str:
    """Normalize a reason string into a stable pressure-id fragment."""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def _pressure_trend(current_severity: str, previous: ActivePressure | None) -> str:
    """Compare current severity with the previous pressure severity."""

    if previous is None:
        return "unknown"
    current_rank = SEVERITY_ORDER.get(current_severity, 0)
    previous_rank = SEVERITY_ORDER.get(previous.severity, 0)
    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    return "stable"


def _build_pressure_id(pressure_type: str, dimension: DimensionSnapshot) -> str:
    """Build a stable pressure id from pressure type and dimension reason."""

    reason = str(dimension.evidence.get("reason") or pressure_type)
    return f"pressure-{pressure_type}-{_normalize_reason(reason)}"


__all__ = ["PRESSURE_TYPE_BY_DIMENSION", "SEVERITY_ORDER", "project_active_pressures"]
