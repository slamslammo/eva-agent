"""Linux runtime rate-context builders."""

from __future__ import annotations

from typing import Any

from eva.kernel import ExternalLifeSnapshot, RuntimeState
from eva.l1_sensing.rate_sensors import (
    aggregate_change_magnitude,
    build_rate_context,
    combine_directions,
    metric_change,
    previous_dimension_evidence,
    previous_rate_context,
)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def host_continuity_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    window_sec: float,
) -> dict[str, Any]:
    host_previous = previous_dimension_evidence(previous_snapshot, "host_continuity")
    restart_change = metric_change(
        float(facts["recent_restart_count"]),
        _as_float(host_previous.get("recent_restart_count")),
        facts["elapsed_sec"],
    )
    drift_change = metric_change(
        facts["schedule_drift_sec"],
        _as_float(host_previous.get("schedule_drift_sec")),
        facts["elapsed_sec"],
    )
    return build_rate_context(
        available=bool(facts["rate_available"]),
        direction=combine_directions(
            restart_change["direction"],
            drift_change["direction"],
        ),
        raw_magnitude=aggregate_change_magnitude(restart_change, drift_change),
        previous_rate=previous_rate_context(previous_snapshot, "host_continuity"),
        aggregation_method="ewma",
        extra={
            "elapsed_sec": facts["elapsed_sec"],
            "window_sec": window_sec,
            "restart_count_delta": restart_change["delta"],
            "restart_change_per_sec": restart_change["change_per_sec"],
            "restart_rate_per_sec": facts["recent_restart_count"] / window_sec,
            "restart_direction": restart_change["direction"],
            "schedule_drift_delta": drift_change["delta"],
            "schedule_drift_change_per_sec": drift_change["change_per_sec"],
            "schedule_drift_direction": drift_change["direction"],
        },
    )


def runtime_integrity_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    runtime_state: RuntimeState,
    window_sec: float,
) -> dict[str, Any]:
    runtime_previous = previous_dimension_evidence(previous_snapshot, "runtime_integrity")
    yield_change = metric_change(
        float(facts["recent_yield_count"]),
        _as_float(runtime_previous.get("recent_yield_count")),
        facts["elapsed_sec"],
    )
    distress_change = metric_change(
        float(facts["recent_distress_count"]),
        _as_float(runtime_previous.get("recent_distress_count")),
        facts["elapsed_sec"],
    )
    heartbeat_age_change = metric_change(
        float(runtime_state.heartbeat_age_sec),
        _as_float(runtime_previous.get("heartbeat_age_sec")),
        facts["elapsed_sec"],
    )
    failure_change = metric_change(
        float(runtime_state.consecutive_failures),
        _as_float(runtime_previous.get("consecutive_failures")),
        facts["elapsed_sec"],
    )
    return build_rate_context(
        available=bool(facts["rate_available"]),
        direction=combine_directions(
            distress_change["direction"],
            yield_change["direction"],
            heartbeat_age_change["direction"],
            failure_change["direction"],
        ),
        raw_magnitude=aggregate_change_magnitude(
            distress_change,
            yield_change,
            heartbeat_age_change,
            failure_change,
        ),
        previous_rate=previous_rate_context(previous_snapshot, "runtime_integrity"),
        aggregation_method="ewma",
        extra={
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
        },
    )


def resource_state_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
) -> dict[str, Any]:
    resource_previous = previous_dimension_evidence(previous_snapshot, "resource_state")
    disk_change = metric_change(
        float(facts["disk_usage"].free),
        _as_float(resource_previous.get("disk_free_bytes")),
        facts["elapsed_sec"],
        higher_is_worse=False,
    )
    return build_rate_context(
        available=bool(facts["rate_available"]),
        direction=disk_change["direction"],
        raw_magnitude=aggregate_change_magnitude(disk_change),
        previous_rate=previous_rate_context(previous_snapshot, "resource_state"),
        aggregation_method="first_order_diff",
        extra={
            "elapsed_sec": facts["elapsed_sec"],
            "disk_free_bytes_delta": disk_change["delta"],
            "disk_free_change_per_sec": disk_change["change_per_sec"],
            "disk_free_direction": disk_change["direction"],
        },
    )


def anomaly_accumulation_rate_context(
    *,
    facts: dict[str, Any],
    previous_snapshot: ExternalLifeSnapshot | None,
    window_sec: float,
) -> dict[str, Any]:
    anomaly_previous = previous_dimension_evidence(previous_snapshot, "anomaly_accumulation")
    error_change = metric_change(
        float(facts["recent_error_count"]),
        _as_float(anomaly_previous.get("recent_error_count")),
        facts["elapsed_sec"],
    )
    anomaly_yield_change = metric_change(
        float(facts["recent_yield_count"]),
        _as_float(anomaly_previous.get("recent_yield_count")),
        facts["elapsed_sec"],
    )
    anomaly_distress_change = metric_change(
        float(facts["recent_distress_count"]),
        _as_float(anomaly_previous.get("recent_distress_count")),
        facts["elapsed_sec"],
    )
    anomaly_restart_change = metric_change(
        float(facts["recent_restart_count"]),
        _as_float(anomaly_previous.get("recent_restart_count")),
        facts["elapsed_sec"],
    )
    anomaly_count_change = metric_change(
        float(facts["anomaly_count"]),
        _as_float(anomaly_previous.get("anomaly_count")),
        facts["elapsed_sec"],
    )
    return build_rate_context(
        available=bool(facts["rate_available"]),
        direction=combine_directions(
            anomaly_count_change["direction"],
            error_change["direction"],
            anomaly_yield_change["direction"],
            anomaly_distress_change["direction"],
            anomaly_restart_change["direction"],
        ),
        raw_magnitude=aggregate_change_magnitude(
            anomaly_count_change,
            error_change,
            anomaly_yield_change,
            anomaly_distress_change,
            anomaly_restart_change,
        ),
        previous_rate=previous_rate_context(previous_snapshot, "anomaly_accumulation"),
        aggregation_method="ewma",
        extra={
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
        },
    )


__all__ = [
    "anomaly_accumulation_rate_context",
    "host_continuity_rate_context",
    "resource_state_rate_context",
    "runtime_integrity_rate_context",
]
