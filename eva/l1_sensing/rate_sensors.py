"""Canonical generic rate/trend derivation helpers for L1 sensing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import ExternalLifeSnapshot


def _as_float(value: Any) -> float | None:
    """Convert a numeric value into float when possible."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



def _change_direction(delta: float, *, higher_is_worse: bool) -> str:
    """Map one numeric delta into worsening/improving/stable."""

    if delta > 0:
        return "worsening" if higher_is_worse else "improving"
    if delta < 0:
        return "improving" if higher_is_worse else "worsening"
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



def combine_directions(*directions: str) -> str:
    """Collapse metric-level directions into one coarse dimension direction."""

    known = [direction for direction in directions if direction != "unknown"]
    if not known:
        return "unknown"
    if "worsening" in known:
        return "worsening"
    if "improving" in known:
        return "improving"
    return "stable"



def elapsed_since_previous(previous_snapshot: ExternalLifeSnapshot | None, now: datetime) -> float | None:
    """Return elapsed seconds since the previous snapshot capture time."""

    if previous_snapshot is None:
        return None
    return max((now - previous_snapshot.captured_at).total_seconds(), 0.0)


__all__ = [
    "combine_directions",
    "elapsed_since_previous",
    "metric_change",
    "previous_dimension_evidence",
]
