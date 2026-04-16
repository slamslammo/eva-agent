"""Collect raw external-life signals from runtime files and recent event history."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Any

from .config import ExternalLifeConfig
from .state import RuntimeState, StateStore, from_iso8601


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


def collect_external_life_inputs(
    store: StateStore,
    runtime_state: RuntimeState,
    config: ExternalLifeConfig,
    now: datetime,
    *,
    due_at: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    """Collect the raw signals used by Step 1 judgment and pressure generation."""

    store.ensure_runtime_dir()
    recent_events = _recent_events(store, now, config.recent_event_window_sec)
    runtime_dir = store.paths.runtime_dir
    runtime_exists = runtime_dir.exists()
    runtime_writable = runtime_exists and os.access(runtime_dir, os.W_OK)

    # If the runtime directory is gone, sample disk usage from the closest existing parent.
    usage_path = runtime_dir if runtime_exists else runtime_dir.parent
    disk_usage = shutil.disk_usage(usage_path)
    recent_restart_count = _count_events(recent_events, "startup")
    recent_yield_count = _count_events(recent_events, "yield")
    recent_distress_count = _count_events(recent_events, "distress")
    recent_error_count = _count_events(recent_events, "error")

    # Drift is only meaningful for scheduled patrol work that had a due time.
    schedule_drift_sec = 0.0 if due_at is None else max((now - due_at).total_seconds(), 0.0)
    return {
        "host_continuity": {
            "process_running": True,
            "recent_restart_count": recent_restart_count,
            "schedule_drift_sec": schedule_drift_sec,
        },
        "runtime_integrity": {
            "instance_valid": runtime_state.instance_valid,
            "runtime_writable": runtime_writable,
            "active_instance_present": store.paths.active_instance_file.exists(),
            "runtime_state_present": store.paths.runtime_state_file.exists(),
            "events_present": store.paths.events_file.exists(),
            "lock_present": store.paths.lock_file.exists(),
            "recent_yield_count": recent_yield_count,
            "recent_distress_count": recent_distress_count,
        },
        "resource_state": {
            "runtime_path_exists": runtime_exists,
            "runtime_writable": runtime_writable,
            "disk_free_bytes": disk_usage.free,
        },
        "anomaly_accumulation": {
            "recent_error_count": recent_error_count,
            "recent_yield_count": recent_yield_count,
            "recent_distress_count": recent_distress_count,
            "recent_restart_count": recent_restart_count,
        },
    }
