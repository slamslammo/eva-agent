"""Canonical generic rate/trend derivation helpers for L1 sensing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import ExternalLifeSnapshot

RATE_SENSING_AGGREGATION_METHODS = frozenset({"linear_regression", "ewma", "first_order_diff"})
_RATE_DIRECTION_ALIASES = {"worsening": "degrading"}


def _as_float(value: Any) -> float | None:
    """Convert a numeric value into float when possible."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



def normalize_rate_direction(direction: object) -> str:
    """Normalize legacy and current rate-direction labels into the v0.6.1 shape."""

    if not isinstance(direction, str):
        return "unknown"
    normalized = _RATE_DIRECTION_ALIASES.get(direction, direction)
    if normalized in {"degrading", "improving", "stable", "unknown"}:
        return normalized
    return "unknown"



def _change_direction(delta: float, *, higher_is_worse: bool) -> str:
    """Map one numeric delta into degrading/improving/stable."""

    if delta > 0:
        return "degrading" if higher_is_worse else "improving"
    if delta < 0:
        return "improving" if higher_is_worse else "degrading"
    return "stable"



def metric_change(
    current_value: float,
    previous_value: float | None,
    elapsed_sec: float | None,
    *,
    higher_is_worse: bool = True,
) -> dict[str, Any]:
    """Describe how one metric changed relative to the previous snapshot."""

    if previous_value is None or elapsed_sec is None or elapsed_sec <= 0:
        return {
            "delta": None,
            "direction": "unknown",
            "change_per_sec": None,
        }
    delta = current_value - previous_value
    return {
        "delta": delta,
        "direction": _change_direction(delta, higher_is_worse=higher_is_worse),
        "change_per_sec": delta / elapsed_sec,
    }



def previous_dimension_evidence(
    previous_snapshot: ExternalLifeSnapshot | None,
    dimension_name: str,
) -> dict[str, Any]:
    """Return the previous persisted evidence for one dimension."""

    if previous_snapshot is None:
        return {}
    snapshot = previous_snapshot.dimensions.get(dimension_name)
    if snapshot is None:
        return {}
    return dict(snapshot.evidence)



def previous_rate_context(
    previous_snapshot: ExternalLifeSnapshot | None,
    dimension_name: str,
) -> dict[str, Any]:
    """Return the previous persisted rate-context payload for one dimension."""

    evidence = previous_dimension_evidence(previous_snapshot, dimension_name)
    value = evidence.get("rate_context")
    return dict(value) if isinstance(value, dict) else {}



def combine_directions(*directions: str) -> str:
    """Collapse metric-level directions into one coarse dimension direction."""

    known = [normalize_rate_direction(direction) for direction in directions]
    known = [direction for direction in known if direction != "unknown"]
    if not known:
        return "unknown"
    if "degrading" in known:
        return "degrading"
    if "improving" in known:
        return "improving"
    return "stable"



def change_magnitude(change: dict[str, Any]) -> float | None:
    """Return the usable magnitude for one metric-change payload."""

    per_sec = _as_float(change.get("change_per_sec"))
    if per_sec is not None:
        return abs(per_sec)
    delta = _as_float(change.get("delta"))
    if delta is not None:
        return abs(delta)
    return None



def aggregate_change_magnitude(*changes: dict[str, Any]) -> float | None:
    """Return the largest available metric-change magnitude from a compound rate surface."""

    magnitudes = [magnitude for magnitude in (change_magnitude(change) for change in changes) if magnitude is not None]
    if not magnitudes:
        return None
    return max(magnitudes)



def unavailable_rate_context(**extra: Any) -> dict[str, Any]:
    """Return the canonical unavailable-rate payload."""

    payload = {
        "available": False,
        "direction": "unknown",
        "magnitude": None,
        "acceleration": None,
    }
    payload.update(extra)
    return payload



def _smoothed_magnitude(
    raw_magnitude: float | None,
    previous_rate: dict[str, Any],
    aggregation_method: str,
) -> float | None:
    """Return the declared aggregation-method magnitude projection."""

    if raw_magnitude is None:
        return None
    if aggregation_method != "ewma":
        return raw_magnitude
    previous_magnitude = _as_float(previous_rate.get("magnitude"))
    if previous_magnitude is None:
        return raw_magnitude
    return (0.6 * raw_magnitude) + (0.4 * previous_magnitude)



def _rate_acceleration(current_magnitude: float | None, previous_rate: dict[str, Any]) -> str | None:
    """Compare current and previous magnitudes into the v0.6.1 acceleration label."""

    if current_magnitude is None:
        return None
    previous_magnitude = _as_float(previous_rate.get("magnitude"))
    if previous_magnitude is None:
        return None
    delta = current_magnitude - previous_magnitude
    if delta > 1e-9:
        return "increasing"
    if delta < -1e-9:
        return "decreasing"
    return "stable"



def build_rate_context(
    *,
    available: bool,
    direction: str,
    raw_magnitude: float | None,
    previous_rate: dict[str, Any] | None = None,
    aggregation_method: str = "first_order_diff",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one canonical rate-context payload from raw direction and magnitude."""

    payload = dict(extra or {})
    payload["aggregation_method"] = aggregation_method
    if not available:
        return unavailable_rate_context(**payload)
    previous = previous_rate or {}
    magnitude = _smoothed_magnitude(raw_magnitude, previous, aggregation_method)
    payload.update(
        {
            "available": True,
            "direction": normalize_rate_direction(direction),
            "magnitude": magnitude,
            "acceleration": _rate_acceleration(magnitude, previous),
        }
    )
    return payload



def elapsed_since_previous(previous_snapshot: ExternalLifeSnapshot | None, now: datetime) -> float | None:
    """Return elapsed seconds since the previous snapshot capture time."""

    if previous_snapshot is None:
        return None
    return max((now - previous_snapshot.captured_at).total_seconds(), 0.0)


__all__ = [
    "RATE_SENSING_AGGREGATION_METHODS",
    "aggregate_change_magnitude",
    "build_rate_context",
    "change_magnitude",
    "combine_directions",
    "elapsed_since_previous",
    "metric_change",
    "normalize_rate_direction",
    "previous_dimension_evidence",
    "previous_rate_context",
    "unavailable_rate_context",
]
