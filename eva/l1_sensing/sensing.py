"""Collect raw external-life signals from runtime files and recent event history."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Any

from ..kernel import ExternalLifeConfig, ExternalLifeSnapshot, RuntimeState, StateStore, from_iso8601
from .rate_sensors import elapsed_since_previous
from .sensor_registry import SensingContext, build_sensor_registry
from .state_sensors import build_state_sensor_specs


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
    elapsed_sec = elapsed_since_previous(previous_snapshot, now)
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



def default_sensor_registry():
    """Build the baseline ordered registry for current L1 dimensions."""

    return build_sensor_registry(build_state_sensor_specs())



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
