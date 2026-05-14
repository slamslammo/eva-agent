"""Linux runtime anomaly-accumulation sensor specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec


def _anomaly_accumulation_sensor(context: SensingContext) -> SensorOutput:
    """Collect anomaly accumulation evidence from recent event history."""

    from .rate_context import anomaly_accumulation_rate_context
    from eva.l1_sensing.sensor_registry import SensorOutput

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


def build_anomaly_accumulation_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the Linux runtime anomaly-accumulation sensor specs."""

    from eva.l1_sensing.sensor_registry import SensorSpec

    return (SensorSpec(name="anomaly_accumulation", collect=_anomaly_accumulation_sensor),)


__all__ = ["build_anomaly_accumulation_sensor_specs"]
