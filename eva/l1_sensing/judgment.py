"""Turn sensed external-life inputs into deterministic health judgments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import DimensionSnapshot, ExternalLifeConfig, ExternalLifeSnapshot
from .dimension_specs import get_default_dimension_priority_by_name, get_default_dimension_specs
from .rate_sensors import normalize_rate_direction

SEVERITY_ORDER = {"healthy": 0, "degraded": 1, "critical": 2}


def _rank_for_status(value: str) -> int:
    """Return the numeric severity rank for one status label."""

    return SEVERITY_ORDER.get(value, 0)


def _rate_direction(snapshot: DimensionSnapshot | None) -> str:
    """Extract the coarse direction from one dimension snapshot."""

    if snapshot is None:
        return "unknown"
    rate_context = snapshot.evidence.get("rate_context")
    if not isinstance(rate_context, dict):
        return "unknown"
    return normalize_rate_direction(rate_context.get("direction"))


def evaluate_dimensions(inputs: dict[str, dict[str, object]], config: ExternalLifeConfig) -> dict[str, DimensionSnapshot]:
    """Evaluate all currently registered external-life dimensions from raw patrol inputs."""

    dimensions: dict[str, DimensionSnapshot] = {}
    for spec in get_default_dimension_specs():
        if spec.name not in inputs:
            raise ValueError(f"missing registered dimension input: {spec.name}")
        dimensions[spec.name] = spec.snapshot_fn(dict(inputs[spec.name]), config)
    return dimensions


def build_external_life_snapshot(
    cadence: str,
    inputs: dict[str, dict[str, object]],
    config: ExternalLifeConfig,
    now: datetime,
    *,
    previous_snapshot: ExternalLifeSnapshot | None = None,
) -> ExternalLifeSnapshot:
    """Build one judged patrol snapshot from raw sensing inputs."""

    dimensions = evaluate_dimensions(inputs, config)
    overall_status = determine_overall_status(dimensions)
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol=cadence,
        dimensions=dimensions,
        overall_status=overall_status,
        primary_gap=determine_primary_gap(dimensions),
        trend=determine_trend(
            overall_status,
            previous_snapshot,
            current_dimensions=dimensions,
        ),
        updated_at=now,
    )


def _dimension_trend(
    current_dimensions: dict[str, DimensionSnapshot],
    previous_snapshot: ExternalLifeSnapshot,
) -> str:
    """Compare current and previous dimensions when overall severity is unchanged."""

    for spec in get_default_dimension_specs():
        current = current_dimensions.get(spec.name)
        previous = previous_snapshot.dimensions.get(spec.name)
        current_rank = _rank_for_status("healthy" if current is None else current.status)
        previous_rank = _rank_for_status("healthy" if previous is None else previous.status)
        if current_rank > previous_rank:
            return "worsening"
        if current_rank < previous_rank:
            return "improving"
        direction = _rate_direction(current)
        if direction == "degrading":
            return "worsening"
        if direction == "improving":
            return "improving"
    return "stable"


def determine_overall_status(dimensions: dict[str, DimensionSnapshot]) -> str:
    """Collapse per-dimension judgments into the highest-severity overall status."""

    highest = max(_rank_for_status(snapshot.status) for snapshot in dimensions.values())
    for status, rank in SEVERITY_ORDER.items():
        if rank == highest:
            return status
    return "healthy"


def determine_primary_gap(dimensions: dict[str, DimensionSnapshot]) -> dict[str, str]:
    """Return the most severe non-healthy dimension and its reason."""

    priority_by_name = get_default_dimension_priority_by_name()
    ranked = sorted(
        dimensions.items(),
        key=lambda item: (
            -_rank_for_status(item[1].status),
            priority_by_name.get(item[0], len(priority_by_name)),
        ),
    )
    for name, snapshot in ranked:
        if snapshot.status != "healthy":
            return {"type": name, "reason": str(snapshot.evidence.get("reason") or "unknown")}
    return {"type": "none", "reason": "none"}


def determine_trend(
    overall_status: str,
    previous_snapshot: ExternalLifeSnapshot | None,
    *,
    current_dimensions: dict[str, DimensionSnapshot] | None = None,
) -> str:
    """Compare the current status with the previous snapshot."""

    if previous_snapshot is None:
        return "unknown"
    current_rank = _rank_for_status(overall_status)
    previous_rank = _rank_for_status(previous_snapshot.overall_status)
    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    if current_dimensions is not None:
        return _dimension_trend(current_dimensions, previous_snapshot)
    return "stable"
