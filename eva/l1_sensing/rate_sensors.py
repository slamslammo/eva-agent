"""Canonical rate/trend derivation helpers for L1 sensing."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import ExternalLifeSnapshot, RuntimeState


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



def _metric_change(
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



def _previous_dimension_evidence(
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



def _combine_directions(*directions: str) -> str:
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



def host_continuity_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    window_sec: float,
) -> dict[str, Any]:
    """Build rate context for host continuity."""

    host_previous = _previous_dimension_evidence(previous_snapshot, "host_continuity")
    restart_change = _metric_change(
        float(facts["recent_restart_count"]),
        _as_float(host_previous.get("recent_restart_count")),
        facts["elapsed_sec"],
    )
    drift_change = _metric_change(
        facts["schedule_drift_sec"],
        _as_float(host_previous.get("schedule_drift_sec")),
        facts["elapsed_sec"],
    )
    return {
        "available": facts["rate_available"],
        "elapsed_sec": facts["elapsed_sec"],
        "window_sec": window_sec,
        "restart_count_delta": restart_change["delta"],
        "restart_change_per_sec": restart_change["change_per_sec"],
        "restart_rate_per_sec": facts["recent_restart_count"] / window_sec,
        "restart_direction": restart_change["direction"],
        "schedule_drift_delta": drift_change["delta"],
        "schedule_drift_change_per_sec": drift_change["change_per_sec"],
        "schedule_drift_direction": drift_change["direction"],
        "direction": _combine_directions(
            restart_change["direction"],
            drift_change["direction"],
        ),
    }



def runtime_integrity_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    runtime_state: RuntimeState,
    window_sec: float,
) -> dict[str, Any]:
    """Build rate context for runtime integrity."""

    runtime_previous = _previous_dimension_evidence(previous_snapshot, "runtime_integrity")
    yield_change = _metric_change(
        float(facts["recent_yield_count"]),
        _as_float(runtime_previous.get("recent_yield_count")),
        facts["elapsed_sec"],
    )
    distress_change = _metric_change(
        float(facts["recent_distress_count"]),
        _as_float(runtime_previous.get("recent_distress_count")),
        facts["elapsed_sec"],
    )
    heartbeat_age_change = _metric_change(
        float(runtime_state.heartbeat_age_sec),
        _as_float(runtime_previous.get("heartbeat_age_sec")),
        facts["elapsed_sec"],
    )
    failure_change = _metric_change(
        float(runtime_state.consecutive_failures),
        _as_float(runtime_previous.get("consecutive_failures")),
        facts["elapsed_sec"],
    )
    return {
        "available": facts["rate_available"],
        "elapsed_sec": facts["elapsed_sec"],
        "window_sec": window_sec,
        "yield_count_delta": yield_change["delta"],
        "yield_change_per_sec": yield_change["change_per_sec"],
        "yield_rate_per_sec": facts["recent_yield_count"] / window_sec,
        "yield_direction": yield_change["direction"],
        "distress_count_delta": distress_change["delta"],
        "distress_change_per_sec": distress_change["change_per_sec"],
        "distress_rate_per_sec": facts["recent_distress_count"] / window_sec,
        "distress_direction": distress_change["direction"],
        "heartbeat_age_sec_delta": heartbeat_age_change["delta"],
        "heartbeat_age_change_per_sec": heartbeat_age_change["change_per_sec"],
        "heartbeat_age_direction": heartbeat_age_change["direction"],
        "consecutive_failures_delta": failure_change["delta"],
        "consecutive_failures_change_per_sec": failure_change["change_per_sec"],
        "consecutive_failures_direction": failure_change["direction"],
        "direction": _combine_directions(
            distress_change["direction"],
            yield_change["direction"],
            heartbeat_age_change["direction"],
            failure_change["direction"],
        ),
    }



def resource_state_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
) -> dict[str, Any]:
    """Build rate context for resource state."""

    resource_previous = _previous_dimension_evidence(previous_snapshot, "resource_state")
    disk_change = _metric_change(
        float(facts["disk_usage"].free),
        _as_float(resource_previous.get("disk_free_bytes")),
        facts["elapsed_sec"],
        higher_is_worse=False,
    )
    return {
        "available": facts["rate_available"],
        "elapsed_sec": facts["elapsed_sec"],
        "disk_free_bytes_delta": disk_change["delta"],
        "disk_free_change_per_sec": disk_change["change_per_sec"],
        "disk_free_direction": disk_change["direction"],
        "direction": disk_change["direction"],
    }



def anomaly_accumulation_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    window_sec: float,
) -> dict[str, Any]:
    """Build rate context for anomaly accumulation."""

    anomaly_previous = _previous_dimension_evidence(previous_snapshot, "anomaly_accumulation")
    error_change = _metric_change(
        float(facts["recent_error_count"]),
        _as_float(anomaly_previous.get("recent_error_count")),
        facts["elapsed_sec"],
    )
    anomaly_yield_change = _metric_change(
        float(facts["recent_yield_count"]),
        _as_float(anomaly_previous.get("recent_yield_count")),
        facts["elapsed_sec"],
    )
    anomaly_distress_change = _metric_change(
        float(facts["recent_distress_count"]),
        _as_float(anomaly_previous.get("recent_distress_count")),
        facts["elapsed_sec"],
    )
    anomaly_restart_change = _metric_change(
        float(facts["recent_restart_count"]),
        _as_float(anomaly_previous.get("recent_restart_count")),
        facts["elapsed_sec"],
    )
    anomaly_count_change = _metric_change(
        float(facts["anomaly_count"]),
        _as_float(anomaly_previous.get("anomaly_count")),
        facts["elapsed_sec"],
    )
    return {
        "available": facts["rate_available"],
        "elapsed_sec": facts["elapsed_sec"],
        "window_sec": window_sec,
        "recent_error_count_delta": error_change["delta"],
        "error_change_per_sec": error_change["change_per_sec"],
        "error_rate_per_sec": facts["recent_error_count"] / window_sec,
        "error_direction": error_change["direction"],
        "recent_yield_count_delta": anomaly_yield_change["delta"],
        "yield_change_per_sec": anomaly_yield_change["change_per_sec"],
        "yield_rate_per_sec": facts["recent_yield_count"] / window_sec,
        "yield_direction": anomaly_yield_change["direction"],
        "recent_distress_count_delta": anomaly_distress_change["delta"],
        "distress_change_per_sec": anomaly_distress_change["change_per_sec"],
        "distress_rate_per_sec": facts["recent_distress_count"] / window_sec,
        "distress_direction": anomaly_distress_change["direction"],
        "recent_restart_count_delta": anomaly_restart_change["delta"],
        "restart_change_per_sec": anomaly_restart_change["change_per_sec"],
        "restart_rate_per_sec": facts["recent_restart_count"] / window_sec,
        "restart_direction": anomaly_restart_change["direction"],
        "anomaly_count_delta": anomaly_count_change["delta"],
        "anomaly_change_per_sec": anomaly_count_change["change_per_sec"],
        "anomaly_rate_per_sec": facts["anomaly_count"] / window_sec,
        "direction": _combine_directions(
            anomaly_count_change["direction"],
            error_change["direction"],
            anomaly_yield_change["direction"],
            anomaly_distress_change["direction"],
            anomaly_restart_change["direction"],
        ),
    }
