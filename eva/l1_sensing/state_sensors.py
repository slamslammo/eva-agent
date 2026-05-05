"""Canonical concrete state-sensor collectors for L1 sensing."""

from __future__ import annotations

from typing import Callable

from .rate_sensors import (
    anomaly_accumulation_rate_context,
    host_continuity_rate_context,
    resource_state_rate_context,
    runtime_integrity_rate_context,
)
from .sensor_registry import SensingContext, SensorOutput, SensorSpec

BuiltInSensorProvider = Callable[[], tuple[SensorSpec, ...]]


def _host_continuity_sensor(context: SensingContext) -> SensorOutput:
    """Collect host-continuity evidence from shared patrol sampling facts."""

    facts = context.shared_facts
    return SensorOutput(
        dimension="host_continuity",
        payload={
            "process_running": True,
            "recent_restart_count": facts["recent_restart_count"],
            "schedule_drift_sec": facts["schedule_drift_sec"],
            "rate_context": host_continuity_rate_context(
                facts=facts,
                previous_snapshot=context.previous_snapshot,
                window_sec=context.config.recent_event_window_sec,
            ),
        },
    )


def _runtime_integrity_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-integrity evidence from runtime state and shared facts."""

    facts = context.shared_facts
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
            "rate_context": runtime_integrity_rate_context(
                facts=facts,
                previous_snapshot=context.previous_snapshot,
                runtime_state=context.runtime_state,
                window_sec=context.config.recent_event_window_sec,
            ),
        },
    )


def _resource_state_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-path and disk-state evidence."""

    facts = context.shared_facts
    return SensorOutput(
        dimension="resource_state",
        payload={
            "runtime_path_exists": facts["runtime_exists"],
            "runtime_writable": facts["runtime_writable"],
            "disk_free_bytes": facts["disk_usage"].free,
            "rate_context": resource_state_rate_context(
                facts=facts,
                previous_snapshot=context.previous_snapshot,
            ),
        },
    )


def _anomaly_accumulation_sensor(context: SensingContext) -> SensorOutput:
    """Collect anomaly accumulation evidence from recent event history."""

    facts = context.shared_facts
    return SensorOutput(
        dimension="anomaly_accumulation",
        payload={
            "recent_error_count": facts["recent_error_count"],
            "recent_yield_count": facts["recent_yield_count"],
            "recent_distress_count": facts["recent_distress_count"],
            "recent_restart_count": facts["recent_restart_count"],
            "anomaly_count": facts["anomaly_count"],
            "rate_context": anomaly_accumulation_rate_context(
                facts=facts,
                previous_snapshot=context.previous_snapshot,
                window_sec=context.config.recent_event_window_sec,
            ),
        },
    )


def build_host_continuity_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the built-in host-continuity sensor specs."""

    return (SensorSpec(name="host_continuity", collect=_host_continuity_sensor),)


def build_runtime_integrity_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the built-in runtime-integrity sensor specs."""

    return (SensorSpec(name="runtime_integrity", collect=_runtime_integrity_sensor),)


def build_resource_state_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the built-in resource-state sensor specs."""

    return (SensorSpec(name="resource_state", collect=_resource_state_sensor),)


def build_anomaly_accumulation_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the built-in anomaly-accumulation sensor specs."""

    return (SensorSpec(name="anomaly_accumulation", collect=_anomaly_accumulation_sensor),)


def built_in_sensor_providers() -> tuple[BuiltInSensorProvider, ...]:
    """Return the ordered built-in sensor providers for baseline L1 sensing."""

    return (
        build_host_continuity_sensor_specs,
        build_runtime_integrity_sensor_specs,
        build_resource_state_sensor_specs,
        build_anomaly_accumulation_sensor_specs,
    )


def build_state_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the ordered baseline state-sensor specs for current L1 dimensions."""

    specs: list[SensorSpec] = []
    for provider in built_in_sensor_providers():
        specs.extend(provider())
    return tuple(specs)
