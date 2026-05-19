"""Canonical Linux runtime runner for Phase A scenario assembly."""

from __future__ import annotations

from typing import Callable

from eva.kernel.config import RuntimeConfig
from eva.kernel.main import RunSummary, build_runtime_config_from_args, parse_args, print_run_summary, run_runtime
from eva.l1_sensing.sensor_registry import SensorRegistry
from eva.l3_deliberation import WorkingMemoryAdapter
from runners.longrun_validation import longrun_hook_from_args
from scenarios.linux_runtime import activate_linux_runtime_scenario

__all__ = ["main", "run_linux_runtime"]


def run_linux_runtime(
    config: RuntimeConfig,
    *,
    working_memory_adapter: WorkingMemoryAdapter | None = None,
    sensor_registry: SensorRegistry | None = None,
    periodic_hook: Callable[..., tuple[bool, str | None]] | None = None,
    hook_interval_sec: float = 1800.0,
) -> RunSummary:
    """Activate the Linux runtime scenario and execute the generic framework loop."""

    activate_linux_runtime_scenario(inherited_priors_path=config.inherited_priors_path)
    return run_runtime(
        config,
        working_memory_adapter=working_memory_adapter,
        sensor_registry=sensor_registry,
        periodic_hook=periodic_hook,
        hook_interval_sec=hook_interval_sec,
    )


def main() -> None:
    """Build Linux runtime config from CLI arguments and print a short summary."""

    args = parse_args()
    config = build_runtime_config_from_args(args)
    periodic_hook = longrun_hook_from_args(args)
    summary = run_linux_runtime(
        config,
        periodic_hook=periodic_hook,
        hook_interval_sec=args.longrun_hook_interval_sec,
    )
    print_run_summary(summary)


if __name__ == "__main__":
    main()
