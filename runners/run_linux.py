"""Canonical Linux runtime runner for Phase A scenario assembly."""

from __future__ import annotations

from eva.kernel.config import RuntimeConfig
from eva.kernel.main import RunSummary, main as framework_main, run_runtime
from eva.l1_sensing.sensor_registry import SensorRegistry
from eva.l3_deliberation import WorkingMemoryAdapter
from scenarios.linux_runtime import activate_linux_runtime_scenario

__all__ = ["main", "run_linux_runtime"]


def run_linux_runtime(
    config: RuntimeConfig,
    *,
    working_memory_adapter: WorkingMemoryAdapter | None = None,
    sensor_registry: SensorRegistry | None = None,
) -> RunSummary:
    """Activate the Linux runtime scenario and execute the generic framework loop."""

    activate_linux_runtime_scenario()
    return run_runtime(
        config,
        working_memory_adapter=working_memory_adapter,
        sensor_registry=sensor_registry,
    )


def main() -> None:
    """Activate the Linux runtime scenario and delegate CLI execution to the framework entry."""

    activate_linux_runtime_scenario()
    framework_main()


if __name__ == "__main__":
    main()
