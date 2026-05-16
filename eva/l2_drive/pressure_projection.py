"""Readonly compatibility pressure projection from judged gaps."""

from __future__ import annotations

import re
from typing import Any

from ..kernel import ActivePressure, ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot

SEVERITY_ORDER = {"healthy": 0, "degraded": 1, "critical": 2}


def _normalize_rate_direction(direction: object) -> str:
    if not isinstance(direction, str):
        return "unknown"
    if direction == "worsening":
        direction = "degrading"
    if direction in {"degrading", "improving", "stable", "unknown"}:
        return direction
    return "unknown"


def project_active_pressures(
    snapshot: ExternalLifeSnapshot,
    previous_table: ActivePressureTable,
) -> list[ActivePressure]:
    """Project judged gaps into compatibility pressure records."""

    previous_by_id = {pressure.pressure_id: pressure for pressure in previous_table.pressures}
    from ..l1_sensing.dimension_specs import (
        get_default_dimension_spec_by_name,
        get_default_pressure_type_by_dimension_name,
    )

    pressure_type_by_dimension = get_default_pressure_type_by_dimension_name()
    spec_by_dimension = get_default_dimension_spec_by_name()
    current_pressures: list[ActivePressure] = []
    for dimension_name, dimension in snapshot.dimensions.items():
        spec = spec_by_dimension[dimension_name]
        anticipatory = _is_anticipatory_pressure(spec, dimension)
        if dimension.status == "healthy" and not anticipatory:
            continue
        evidence = _pressure_evidence(dimension_name, dimension, spec, anticipatory=anticipatory)
        pressure_type = pressure_type_by_dimension[dimension_name]
        pressure_id = _build_pressure_id(snapshot, pressure_type, str(evidence.get("reason") or pressure_type))
        previous = previous_by_id.get(pressure_id)
        severity = "degraded" if anticipatory else dimension.status
        current_pressures.append(
            ActivePressure(
                pressure_id=pressure_id,
                type=pressure_type,
                severity=severity,
                evidence=evidence,
                first_seen_at=snapshot.captured_at if previous is None else previous.first_seen_at,
                last_seen_at=snapshot.captured_at,
                trend=_pressure_trend(severity, previous, evidence),
                active=True,
            )
        )
    return current_pressures


def _normalize_reason(value: str) -> str:
    """Normalize a reason string into a stable pressure-id fragment."""

    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def _rate_context(dimension: DimensionSnapshot) -> dict[str, Any]:
    value = dimension.evidence.get("rate_context")
    return dict(value) if isinstance(value, dict) else {}


def _rate_magnitude(dimension: DimensionSnapshot) -> float | None:
    value = _rate_context(dimension).get("magnitude")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_anticipatory_pressure(spec: Any, dimension: DimensionSnapshot) -> bool:
    if dimension.status != "healthy":
        return False
    if getattr(spec, "rate_sensing_tier", None) != "required":
        return False
    threshold = getattr(spec, "rate_anticipatory_threshold", None)
    if threshold is None:
        return False
    rate_context = _rate_context(dimension)
    if not bool(rate_context.get("available")):
        return False
    if _normalize_rate_direction(rate_context.get("direction")) != "degrading":
        return False
    magnitude = _rate_magnitude(dimension)
    return magnitude is not None and magnitude >= float(threshold)


def _pressure_reason(dimension_name: str, dimension: DimensionSnapshot, *, anticipatory: bool) -> str:
    if anticipatory:
        return f"{dimension_name}_degrading"
    return str(dimension.evidence.get("reason") or dimension_name)


def _pressure_urgency(dimension: DimensionSnapshot, spec: Any, *, anticipatory: bool) -> str:
    rate_context = _rate_context(dimension)
    direction = _normalize_rate_direction(rate_context.get("direction"))
    magnitude = _rate_magnitude(dimension)
    if anticipatory:
        threshold = float(getattr(spec, "rate_anticipatory_threshold", 0.0) or 0.0)
        if magnitude is not None and threshold > 0 and magnitude >= threshold * 2:
            return "high"
        return "normal"
    if dimension.status == "critical":
        return "normal" if direction == "improving" else "high"
    if dimension.status == "degraded":
        if direction == "degrading":
            return "high"
        if direction == "improving":
            return "low"
        return "normal"
    return "low"


def _pressure_evidence(dimension_name: str, dimension: DimensionSnapshot, spec: Any, *, anticipatory: bool) -> dict[str, Any]:
    evidence = dict(dimension.evidence)
    evidence["source_reason"] = str(dimension.evidence.get("reason") or "unknown")
    evidence["reason"] = _pressure_reason(dimension_name, dimension, anticipatory=anticipatory)
    evidence["baseline_status"] = dimension.status
    evidence["anticipatory"] = anticipatory
    evidence["pressure_mode"] = "anticipatory" if anticipatory else "baseline"
    evidence["urgency"] = _pressure_urgency(dimension, spec, anticipatory=anticipatory)
    if anticipatory:
        evidence["anticipatory_threshold"] = getattr(spec, "rate_anticipatory_threshold", None)
    return evidence


def _pressure_trend(current_severity: str, previous: ActivePressure | None, evidence: dict[str, Any]) -> str:
    """Compare current pressure state with the previous pressure state."""

    if previous is None:
        return "unknown"
    current_rank = SEVERITY_ORDER.get(current_severity, 0)
    previous_rank = SEVERITY_ORDER.get(previous.severity, 0)
    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    rate_context = evidence.get("rate_context")
    if isinstance(rate_context, dict):
        direction = _normalize_rate_direction(rate_context.get("direction"))
        if direction == "degrading":
            return "worsening"
        if direction == "improving":
            return "improving"
    return "stable"


def _build_pressure_id(snapshot: ExternalLifeSnapshot, pressure_type: str, reason: str) -> str:
    """Build a stable pressure id from scenario name, pressure type, and pressure reason."""

    from ..scenario_bundle import get_active_runtime_scenario

    scenario_name = get_active_runtime_scenario().name
    return f"pressure-{scenario_name}-{pressure_type}-{_normalize_reason(reason)}"


__all__ = ["SEVERITY_ORDER", "project_active_pressures"]
