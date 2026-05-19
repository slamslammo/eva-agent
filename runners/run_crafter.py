"""Canonical Crafter runtime runner for Stage H end-to-end validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from typing import Callable

from eva.kernel.config import RuntimeConfig
from eva.kernel.main import (
    RunSummary,
    build_runtime_config_from_args,
    parse_args,
    print_run_summary,
    run_runtime,
)
from eva.l1_sensing.sensor_registry import SensorRegistry
from eva.l3_deliberation import WorkingMemoryAdapter
from runners.longrun_validation import longrun_hook_from_args
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.wrapper import CrafterEnvWrapper, StepResult

__all__ = ["CrafterActionStep", "CrafterRuntimeSession", "main", "run_crafter_runtime"]


@dataclass(frozen=True)
class CrafterActionStep:
    raw_observation: Any
    reward: float
    done: bool
    raw_info: dict[str, Any]
    agent_observation: dict[str, Any]
    before_observation: dict[str, Any]
    after_action_observation: dict[str, Any]


@dataclass
class CrafterRuntimeSession:
    wrapper: CrafterEnvWrapper
    latest_agent_observation: dict[str, Any]

    @classmethod
    def start(cls, *, seed: int | None = None) -> "CrafterRuntimeSession":
        wrapper = CrafterEnvWrapper(seed=seed)
        return cls(wrapper=wrapper, latest_agent_observation=wrapper.reset(seed=seed))

    def build_shared_facts(self) -> dict[str, Any]:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str) -> CrafterActionStep:
        before_observation = dict(self.latest_agent_observation)
        step_result: StepResult = self.wrapper.step(action_name)
        after_action_observation = dict(step_result.agent_observation)
        next_observation = after_action_observation if not step_result.done else self.wrapper.reset()
        self.latest_agent_observation = next_observation
        return CrafterActionStep(
            raw_observation=step_result.raw_observation,
            reward=step_result.reward,
            done=step_result.done,
            raw_info=dict(step_result.raw_info),
            agent_observation=dict(next_observation),
            before_observation=before_observation,
            after_action_observation=after_action_observation,
        )

    def close(self) -> None:
        self.wrapper.close()


def run_crafter_runtime(
    config: RuntimeConfig,
    *,
    working_memory_adapter: WorkingMemoryAdapter | None = None,
    sensor_registry: SensorRegistry | None = None,
    periodic_hook: Callable[..., tuple[bool, str | None]] | None = None,
    hook_interval_sec: float = 1800.0,
) -> RunSummary:
    """Activate the Crafter scenario and execute the generic framework loop."""

    activate_crafter_scenario(inherited_priors_path=config.inherited_priors_path)
    session = CrafterRuntimeSession.start()
    try:
        return run_runtime(
            config,
            working_memory_adapter=working_memory_adapter,
            sensor_registry=sensor_registry,
            extra_shared_facts_provider=session.build_shared_facts,
            action_runtime=session,
            periodic_hook=periodic_hook,
            hook_interval_sec=hook_interval_sec,
        )
    finally:
        session.close()


def main() -> None:
    """Build Crafter runtime config from CLI arguments and print a short summary."""

    args = parse_args()
    config = build_runtime_config_from_args(args)
    periodic_hook = longrun_hook_from_args(args)
    summary = run_crafter_runtime(
        config,
        periodic_hook=periodic_hook,
        hook_interval_sec=args.longrun_hook_interval_sec,
    )
    print_run_summary(summary)


if __name__ == "__main__":
    main()
