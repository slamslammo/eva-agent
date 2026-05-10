"""Linux runtime resource-state sensor specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext, SensorOutput, SensorSpec


def _resource_state_sensor(context: SensingContext) -> SensorOutput:
    """Collect runtime-path and disk-state evidence."""

    from eva.l1_sensing.rate_sensors import resource_state_rate_context
    from eva.l1_sensing.sensor_registry import SensorOutput

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


def build_resource_state_sensor_specs() -> tuple[SensorSpec, ...]:
    """Return the Linux runtime resource-state sensor specs."""

    from eva.l1_sensing.sensor_registry import SensorSpec

    return (SensorSpec(name="resource_state", collect=_resource_state_sensor),)


__all__ = ["build_resource_state_sensor_specs"]
