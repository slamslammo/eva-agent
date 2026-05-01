"""Collect raw external-life signals from runtime files and recent event history."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Any

from ..kernel import ExternalLifeConfig, ExternalLifeSnapshot, RuntimeState, StateStore, from_iso8601
from .sensor_registry import SensingContext, SensorOutput, SensorSpec, build_sensor_registry


def _recent_events(store: StateStore, now: datetime, window_sec: float) -> list[dict[str, Any]]:
    """Return events whose timestamps fall inside the configured recent window."""

    lower_bound = now.timestamp() - window_sec
    recent: list[dict[str, Any]] = []
    for event in store.read_events():
        timestamp = from_iso8601(event.get("timestamp"))
        if timestamp is None:
            continue
        if timestamp.timestamp() >= lower_bound:
            recent.append(event)
    return recent


def _count_events(events: list[dict[str, Any]], event_type: str) -> int:
    """Count how many recent events match the requested type."""

    return sum(1 for event in events if event.get("event_type") == event_type)


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


def _elapsed_since_previous(previous_snapshot: ExternalLifeSnapshot | None, now: datetime) -> float | None:
    """Return elapsed seconds since the previous snapshot capture time."""

    if previous_snapshot is None:
        return None
    return max((now - previous_snapshot.captured_at).total_seconds(), 0.0)


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


def _build_shared_facts(
    store: StateStore,
    runtime_state: RuntimeState,
    config: ExternalLifeConfig,
    now: datetime,
    *,
    due_at: datetime | None,
    previous_snapshot: ExternalLifeSnapshot | None,
) -> dict[str, Any]:
    """Sample shared facts once so individual sensors stay narrow."""

    store.ensure_runtime_dir()
    recent_events = _recent_events(store, now, config.recent_event_window_sec)
    runtime_dir = store.paths.runtime_dir
    runtime_exists = runtime_dir.exists()
    runtime_writable = runtime_exists and os.access(runtime_dir, os.W_OK)
    usage_path = runtime_dir if runtime_exists else runtime_dir.parent
    disk_usage = shutil.disk_usage(usage_path)
    recent_restart_count = _count_events(recent_events, "startup")
    recent_yield_count = _count_events(recent_events, "yield")
    recent_distress_count = _count_events(recent_events, "distress")
    recent_error_count = _count_events(recent_events, "error")
    anomaly_count = recent_error_count + recent_yield_count + recent_distress_count + max(recent_restart_count - 1, 0)
    schedule_drift_sec = 0.0 if due_at is None else max((now - due_at).total_seconds(), 0.0)
    elapsed_sec = _elapsed_since_previous(previous_snapshot, now)
    rate_available = elapsed_sec is not None and elapsed_sec > 0

    return {
        "recent_events": recent_events,
        "runtime_exists": runtime_exists,
        "runtime_writable": runtime_writable,
        "disk_usage": disk_usage,
        "recent_restart_count": recent_restart_count,
        "recent_yield_count": recent_yield_count,
        "recent_distress_count": recent_distress_count,
        "recent_error_count": recent_error_count,
        "anomaly_count": anomaly_count,
        "schedule_drift_sec": schedule_drift_sec,
        "elapsed_sec": elapsed_sec,
        "rate_available": rate_available,
    }


def _host_continuity_sensor(context: SensingContext) -> SensorOutput:
    """Collect host-continuity evidence from shared patrol sampling facts."""

    facts = context.shared_facts
    host_previous = _previous_dimension_evidence(context.previous_snapshot, "host_continuity")
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
    return SensorOutput(
        dimension="host_continuity",
        payload={
            "process_running": True,
            "recent_restart_count": facts["recent_restart_count"],
            "schedule_drift_sec": facts["schedule_drift_sec"],
            "rate_context": {
                "available": facts["rate_available"],
                "elapsed_sec": facts["elapsed_sec"],
                "window_sec": context.config.recent_event_window_sec,
                "restart_count_delta": restart_change["delta"],
                "restart_change_per_sec": restart_change["change_per_sec"],
                "restart_rate_per_sec": facts["recent_restart_count"] / context.config.recent_event_window_sec,
                "restart_direction": restart_change["direction"],
                "schedule_drift_delta": drift_change["delta"],
                "schedule_drift_change_per_sec": drift_change["change_per_sec"],
                "schedule_drift_direction": drift_change["direction"],
                "direction": _combine_directions(
                    restart_change["direction"],
                    drift_change["direction"],
                ),
            },
        },
    )


def _runtime_integrity_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-integrity evidence from runtime state and shared facts."""

    facts = context.shared_facts
    runtime_previous = _previous_dimension_evidence(context.previous_snapshot, "runtime_integrity")
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
        float(context.runtime_state.heartbeat_age_sec),
        _as_float(runtime_previous.get("heartbeat_age_sec")),
        facts["elapsed_sec"],
    )
    failure_change = _metric_change(
        float(context.runtime_state.consecutive_failures),
        _as_float(runtime_previous.get("consecutive_failures")),
        facts["elapsed_sec"],
    )
    return SensorOutput(
        dimension="runtime_integrity",
        payload={
            "instance_valid": context.runtime_state.instance_valid,
            "runtime_writable": facts["runtime_writable"],
            "active_instance_present": context.store.paths.active_instance_file.exists(),
            "runtime_state_present": context.store.paths.runtime_state_file.exists(),
            "events_present": context.store.paths.events_file.exists(),
            "lock_present": context.store.paths.lock_file.exists(),
            "recent_yield_count": facts["recent_yield_count"],
            "recent_distress_count": facts["recent_distress_count"],
            "heartbeat_age_sec": context.runtime_state.heartbeat_age_sec,
            "consecutive_failures": context.runtime_state.consecutive_failures,
            "rate_context": {
                "available": facts["rate_available"],
                "elapsed_sec": facts["elapsed_sec"],
                "window_sec": context.config.recent_event_window_sec,
                "yield_count_delta": yield_change["delta"],
                "yield_change_per_sec": yield_change["change_per_sec"],
                "yield_rate_per_sec": facts["recent_yield_count"] / context.config.recent_event_window_sec,
                "yield_direction": yield_change["direction"],
                "distress_count_delta": distress_change["delta"],
                "distress_change_per_sec": distress_change["change_per_sec"],
                "distress_rate_per_sec": facts["recent_distress_count"] / context.config.recent_event_window_sec,
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
            },
        },
    )


def _resource_state_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-path and disk-state evidence."""

    facts = context.shared_facts
    resource_previous = _previous_dimension_evidence(context.previous_snapshot, "resource_state")
    disk_change = _metric_change(
        float(facts["disk_usage"].free),
        _as_float(resource_previous.get("disk_free_bytes")),
        facts["elapsed_sec"],
        higher_is_worse=False,
    )
    return SensorOutput(
        dimension="resource_state",
        payload={
            "runtime_path_exists": facts["runtime_exists"],
            "runtime_writable": facts["runtime_writable"],
            "disk_free_bytes": facts["disk_usage"].free,
            "rate_context": {
                "available": facts["rate_available"],
                "elapsed_sec": facts["elapsed_sec"],
                "disk_free_bytes_delta": disk_change["delta"],
                "disk_free_change_per_sec": disk_change["change_per_sec"],
                "disk_free_direction": disk_change["direction"],
                "direction": disk_change["direction"],
            },
        },
    )


def _anomaly_accumulation_sensor(context: SensingContext) -> SensorOutput:
    """Collect anomaly accumulation evidence from recent event history."""

    facts = context.shared_facts
    anomaly_previous = _previous_dimension_evidence(context.previous_snapshot, "anomaly_accumulation")
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
    return SensorOutput(
        dimension="anomaly_accumulation",
        payload={
            "recent_error_count": facts["recent_error_count"],
            "recent_yield_count": facts["recent_yield_count"],
            "recent_distress_count": facts["recent_distress_count"],
            "recent_restart_count": facts["recent_restart_count"],
            "anomaly_count": facts["anomaly_count"],
            "rate_context": {
                "available": facts["rate_available"],
                "elapsed_sec": facts["elapsed_sec"],
                "window_sec": context.config.recent_event_window_sec,
                "recent_error_count_delta": error_change["delta"],
                "error_change_per_sec": error_change["change_per_sec"],
                "error_rate_per_sec": facts["recent_error_count"] / context.config.recent_event_window_sec,
                "error_direction": error_change["direction"],
                "recent_yield_count_delta": anomaly_yield_change["delta"],
                "yield_change_per_sec": anomaly_yield_change["change_per_sec"],
                "yield_rate_per_sec": facts["recent_yield_count"] / context.config.recent_event_window_sec,
                "yield_direction": anomaly_yield_change["direction"],
                "recent_distress_count_delta": anomaly_distress_change["delta"],
                "distress_change_per_sec": anomaly_distress_change["change_per_sec"],
                "distress_rate_per_sec": facts["recent_distress_count"] / context.config.recent_event_window_sec,
                "distress_direction": anomaly_distress_change["direction"],
                "recent_restart_count_delta": anomaly_restart_change["delta"],
                "restart_change_per_sec": anomaly_restart_change["change_per_sec"],
                "restart_rate_per_sec": facts["recent_restart_count"] / context.config.recent_event_window_sec,
                "restart_direction": anomaly_restart_change["direction"],
                "anomaly_count_delta": anomaly_count_change["delta"],
                "anomaly_change_per_sec": anomaly_count_change["change_per_sec"],
                "anomaly_rate_per_sec": facts["anomaly_count"] / context.config.recent_event_window_sec,
                "direction": _combine_directions(
                    anomaly_count_change["direction"],
                    error_change["direction"],
                    anomaly_yield_change["direction"],
                    anomaly_distress_change["direction"],
                    anomaly_restart_change["direction"],
                ),
            },
        },
    )


def default_sensor_registry():
    """Build the baseline ordered registry for current L1 dimensions."""

    return build_sensor_registry(
        [
            SensorSpec(name="host_continuity", collect=_host_continuity_sensor),
            SensorSpec(name="runtime_integrity", collect=_runtime_integrity_sensor),
            SensorSpec(name="resource_state", collect=_resource_state_sensor),
            SensorSpec(name="anomaly_accumulation", collect=_anomaly_accumulation_sensor),
        ]
    )


def collect_external_life_inputs(
    store: StateStore,
    runtime_state: RuntimeState,
    config: ExternalLifeConfig,
    now: datetime,
    *,
    due_at: datetime | None = None,
    previous_snapshot: ExternalLifeSnapshot | None = None,
) -> dict[str, dict[str, Any]]:
    """Collect the raw signals used by Step 1 judgment and pressure generation."""

    context = SensingContext(
        store=store,
        runtime_state=runtime_state,
        config=config,
        now=now,
        due_at=due_at,
        previous_snapshot=previous_snapshot,
        shared_facts=_build_shared_facts(
            store,
            runtime_state,
            config,
            now,
            due_at=due_at,
            previous_snapshot=previous_snapshot,
        ),
    )
    outputs = default_sensor_registry().collect_all(context)
    return {output.dimension: dict(output.payload) for output in outputs}
