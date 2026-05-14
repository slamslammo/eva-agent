"""Linux runtime process/runtime-integrity sensor specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .instance import runtime_integrity_instance_payload

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec


def _runtime_integrity_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-integrity evidence from runtime state and shared facts."""

    from .rate_context import runtime_integrity_rate_context
    from eva.l1_sensing.sensor_registry import SensorOutput

    facts = context.shared_facts
    instance_payload = runtime_integrity_instance_payload(context)
    return SensorOutput(
        dimension="runtime_integrity",
        payload={
            "instance_valid": instance_payload["instance_valid"],
            "runtime_writable": facts["runtime_writable"],
            "active_instance_present": instance_payload["active_instance_present"],
            "runtime_state_present": context.store.paths.runtime_state_file.exists(),
            "events_present": context.store.paths.events_file.exists(),
            "lock_present": instance_payload["lock_present"],
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


def build_runtime_integrity_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the Linux runtime runtime-integrity sensor specs."""

    from eva.l1_sensing.sensor_registry import SensorSpec

    return (SensorSpec(name="runtime_integrity", collect=_runtime_integrity_sensor),)


__all__ = ["build_runtime_integrity_sensor_specs"]
