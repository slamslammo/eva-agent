"""Linux runtime instance-validity evidence fragments."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eva.l1_sensing.sensor_registry import SensingContext


def runtime_integrity_instance_payload(context: SensingContext) -> dict[str, object]:
    """Collect the instance-validity facts used by runtime-integrity sensing."""

    return {
        "instance_valid": context.runtime_state.instance_valid,
        "active_instance_present": context.store.paths.active_instance_file.exists(),
        "lock_present": context.store.paths.lock_file.exists(),
    }


__all__ = ["runtime_integrity_instance_payload"]
