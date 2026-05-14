"""Linux runtime host-continuity sensor specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec


def _host_continuity_sensor(context: SensingContext) -> SensorOutput:
    """Collect host-continuity evidence from shared patrol sampling facts."""

    from .rate_context import host_continuity_rate_context
    from eva.l1_sensing.sensor_registry import SensorOutput

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


def build_host_continuity_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the Linux runtime host-continuity sensor specs."""

    from eva.l1_sensing.sensor_registry import SensorSpec

    return (SensorSpec(name="host_continuity", collect=_host_continuity_sensor),)


__all__ = ["build_host_continuity_sensor_specs"]
