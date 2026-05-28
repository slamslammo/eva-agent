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
from eva.l3_deliberation.memory.working_memory_model_client import (
    MODEL_CLIENT_MODE_LIVE,
    build_live_chat_fn,
)
from eva.l3_deliberation.reasoning.candidate_producer import CandidateProducer
from runners.longrun_validation import longrun_hook_from_args
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions.feasibility import feasible_raw_actions
from scenarios.crafter.reasoning import CrafterLLMActionProducer
from scenarios.crafter.state_packet import build_crafter_state_packet
from scenarios.crafter.world_facts import get_crafter_world_facts_context
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
    # v0.6 rev2: 个体终止标志。HP=0（env done）= 该 individual 真死，kernel loop
    # 读到 terminated 后收尾本 run（exit_reason=individual_terminated），不 reset 续命。
    terminated: bool = False

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
        # v0.6 rev2：Crafter 是单局生存世界，HP=0（done）是该 individual 真死，
        # 无 in-life 复活。**不再 reset 续命** —— 保留终止时的 observation，置
        # terminated 让 kernel loop 把本次 run 作为"一个个体的一生"正常收尾。
        # 下一个体是新的 run（可加载 inherited priors），不是同进程接着跑。
        if step_result.done:
            self.terminated = True
        self.latest_agent_observation = after_action_observation
        return CrafterActionStep(
            raw_observation=step_result.raw_observation,
            reward=step_result.reward,
            done=step_result.done,
            raw_info=dict(step_result.raw_info),
            agent_observation=dict(after_action_observation),
            before_observation=before_observation,
            after_action_observation=after_action_observation,
        )

    def close(self) -> None:
        self.wrapper.close()


def _build_candidate_producer(
    config: RuntimeConfig, session: "CrafterRuntimeSession"
) -> CandidateProducer | None:
    """Build the live CrafterLLMActionProducer for live llm_assisted runs only.

    PR-4: the producer is now CrafterLLMActionProducer (raw-action candidates within
    A'(s)) instead of LLMCandidateProducer (posture + action_hint). Returns None when
    the run is not configured for a live model client so the heuristic path stands.
    """

    if config.working_memory_backend != "llm_assisted":
        return None
    if config.working_memory_model_client_mode != MODEL_CLIENT_MODE_LIVE:
        return None
    client_config = config.working_memory_model_client_config
    timeout_sec = client_config.request_timeout_sec if client_config is not None else 5.0
    chat_fn = build_live_chat_fn(timeout_sec=timeout_sec)
    if chat_fn is None:
        return None
    return CrafterLLMActionProducer(
        chat_fn=chat_fn,
        world_facts_fn=get_crafter_world_facts_context,
        observation_fn=lambda: session.latest_agent_observation,
    )


def run_crafter_runtime(
    config: RuntimeConfig,
    *,
    working_memory_adapter: WorkingMemoryAdapter | None = None,
    candidate_producer: CandidateProducer | None = None,
    sensor_registry: SensorRegistry | None = None,
    periodic_hook: Callable[..., tuple[bool, str | None]] | None = None,
    hook_interval_sec: float = 1800.0,
    seed: int | None = None,
) -> RunSummary:
    """Activate the Crafter scenario and execute the generic framework loop."""

    activate_crafter_scenario(inherited_priors_path=config.inherited_priors_path)
    session = CrafterRuntimeSession.start(seed=seed)
    resolved_producer = candidate_producer or _build_candidate_producer(config, session)
    try:
        return run_runtime(
            config,
            working_memory_adapter=working_memory_adapter,
            sensor_registry=sensor_registry,
            extra_shared_facts_provider=session.build_shared_facts,
            action_runtime=session,
            candidate_producer=resolved_producer,
            seed=seed,
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
        seed=args.seed,
    )
    print_run_summary(summary)


if __name__ == "__main__":
    main()
