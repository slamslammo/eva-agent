"""Runtime entrypoint and bounded loop owned by the kernel namespace."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Any
from uuid import uuid4

from .config import AppendOnlyArtifactsConfig, ExternalLifeConfig, LifecycleConfig, LoopControl, RuntimeConfig, build_runtime_config
from .instance import InstanceGuard
from .lifecycle import ExternalActionRuntime, LifecycleRuntime
from .state import EventRecord, StateStore, emit_log_line, utc_now
from ..l1_sensing.sensor_registry import SensorRegistry
from ..l3_deliberation import (
    ADAPTER_MODE_HEURISTIC,
    ADAPTER_MODE_INERT,
    ClientBackedWorkingMemoryAdapter,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_DEEPSEEK_MODEL,
    HeuristicWorkingMemoryAdapter,
    MODEL_CLIENT_MODE_ANTHROPIC,
    MODEL_CLIENT_MODE_DEEPSEEK,
    MODEL_CLIENT_MODE_HEURISTIC,
    MODEL_CLIENT_MODE_INERT,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapter,
    WorkingMemoryModelClientConfig,
    AnthropicWorkingMemoryModelClient,
    DeepSeekWorkingMemoryModelClient,
    build_builtin_working_memory_adapter,
)

__all__ = [
    "RunSummary",
    "run_runtime",
    "parse_args",
    "build_runtime_config_from_args",
    "print_run_summary",
    "main",
]


@dataclass
class RunSummary:
    """High-level summary returned after one runtime execution."""

    ticks: int
    turns: int
    final_life_state: str
    instance_valid: bool
    runtime_dir: str
    exit_reason: str = "normal"


def run_runtime(
    config: RuntimeConfig,
    *,
    working_memory_adapter: WorkingMemoryAdapter | None = None,
    sensor_registry: SensorRegistry | None = None,
    extra_shared_facts_provider: Callable[[], dict[str, Any] | None] | None = None,
    action_runtime: ExternalActionRuntime | None = None,
    periodic_hook: Callable[..., tuple[bool, str | None]] | None = None,
    hook_interval_sec: float = 1800.0,
) -> RunSummary:
    """Run the lifecycle loop until one of the configured bounds is reached.

    Round 1.D-1: KeyboardInterrupt during the loop is caught; the shutdown
    event is always written before returning. ``RunSummary.exit_reason``
    reports the termination cause (``"normal"`` / ``"max_ticks"`` /
    ``"max_turns"`` / ``"max_runtime_sec"`` / ``"keyboard_interrupt"`` /
    ``"periodic_hook_stop"`` plus optional reason suffix from the hook).

    Round 1.D-2: ``periodic_hook`` (if supplied) is called at most every
    ``hook_interval_sec`` seconds with kwargs ``(runtime_dir,
    elapsed_since_start, ticks, turns)``. Hook returns
    ``(should_stop, reason)``. Hook errors are caught and logged but do
    not crash the loop.
    """

    store = StateStore(
        config.paths,
        append_only_rotation_max_bytes=config.append_only_artifacts.rotation_max_bytes,
    )
    store.ensure_runtime_dir()
    instance_guard = InstanceGuard(config.paths.lock_file, store, config.lifecycle)
    instance_guard.acquire()
    instance_id = f"eva-{utc_now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    active_record = instance_guard.start_instance(instance_id)
    state = store.read_runtime_state()
    now = utc_now()
    state.recovering_until = now + timedelta(seconds=config.lifecycle.recovering_window_sec)
    state.instance_valid = True
    state.updated_at = now
    store.write_runtime_state(state)
    store.append_event(EventRecord(event_type="startup", timestamp=now, instance_id=active_record.instance_id, generation=active_record.generation, details={"runtime_dir": str(config.paths.runtime_dir)}))
    emit_log_line("startup", instance=active_record.instance_id, generation=active_record.generation, runtime_dir=str(config.paths.runtime_dir))

    resolved_adapter = _resolve_working_memory_adapter(config, explicit_adapter=working_memory_adapter)
    working_memory_advisory_source = _working_memory_advisory_source(
        config,
        resolved_adapter=resolved_adapter,
        explicit_adapter=working_memory_adapter,
    )
    runtime = LifecycleRuntime(
        store,
        instance_guard,
        config.lifecycle,
        config.external_life,
        config.working_memory_backend,
        resolved_adapter,
        working_memory_advisory_source,
        sensor_registry,
        extra_shared_facts_provider,
        action_runtime,
    )
    next_heartbeat_at = utc_now()
    started_at = time.monotonic()
    last_hook_at = started_at
    ticks = 0
    turns = 0
    exit_reason = "normal"

    try:
        try:
            while True:
                now = utc_now()
                runtime.queue_due_patrols(now)
                if now >= next_heartbeat_at:
                    runtime.run_tick(state, now=now)
                    ticks += 1
                    next_heartbeat_at = now + timedelta(seconds=config.lifecycle.heartbeat_interval_sec)
                elif runtime.has_pending_work():
                    turn = runtime.run_turn(state, next_heartbeat_at=next_heartbeat_at, now=now)
                    if turn.executed:
                        turns += 1
                    time.sleep(config.control.idle_sleep_sec)
                else:
                    sleep_for = min(config.control.idle_sleep_sec, max((next_heartbeat_at - now).total_seconds(), 0.0))
                    time.sleep(sleep_for)

                if config.control.max_ticks is not None and ticks >= config.control.max_ticks:
                    exit_reason = "max_ticks"
                    break
                if config.control.max_turns is not None and turns >= config.control.max_turns:
                    exit_reason = "max_turns"
                    break
                if config.control.max_runtime_sec is not None and (time.monotonic() - started_at) >= config.control.max_runtime_sec:
                    exit_reason = "max_runtime_sec"
                    break

                # Round 1.D-2: periodic hook for snapshots / tripwires.
                if periodic_hook is not None:
                    monotonic_now = time.monotonic()
                    if monotonic_now - last_hook_at >= hook_interval_sec:
                        last_hook_at = monotonic_now
                        try:
                            should_stop, hook_reason = periodic_hook(
                                runtime_dir=config.paths.runtime_dir,
                                elapsed_since_start=monotonic_now - started_at,
                                ticks=ticks,
                                turns=turns,
                            )
                        except Exception as exc:
                            # Defensive: a buggy hook must not crash a long-run.
                            emit_log_line(
                                "periodic_hook_error",
                                instance=active_record.instance_id,
                                generation=active_record.generation,
                                error=type(exc).__name__,
                                message=str(exc),
                            )
                            should_stop, hook_reason = False, None
                        if should_stop:
                            exit_reason = hook_reason or "periodic_hook_stop"
                            break
        except KeyboardInterrupt:
            # Round 1.D-1: catch and proceed to clean shutdown rather than
            # short-circuiting past the shutdown event write.
            exit_reason = "keyboard_interrupt"

        try:
            final_state = store.read_runtime_state()
        except Exception:
            # If state cannot be re-read, fall back to the in-memory state
            # we've been mutating in the loop.
            final_state = state
        store.append_event(EventRecord(
            event_type="shutdown",
            timestamp=utc_now(),
            instance_id=active_record.instance_id,
            generation=active_record.generation,
            life_state=final_state.life_state,
            details={"ticks": ticks, "turns": turns, "exit_reason": exit_reason},
        ))
        emit_log_line(
            "shutdown",
            instance=active_record.instance_id,
            generation=active_record.generation,
            state=final_state.life_state,
            ticks=ticks,
            turns=turns,
            instance_valid=final_state.instance_valid,
            exit_reason=exit_reason,
        )
        return RunSummary(
            ticks=ticks,
            turns=turns,
            final_life_state=final_state.life_state,
            instance_valid=final_state.instance_valid,
            runtime_dir=str(config.paths.runtime_dir),
            exit_reason=exit_reason,
        )
    finally:
        instance_guard.release()


def _resolve_working_memory_adapter(
    config: RuntimeConfig,
    *,
    explicit_adapter: WorkingMemoryAdapter | None,
) -> WorkingMemoryAdapter | None:
    """Resolve the runtime working-memory adapter while keeping default behavior inert."""

    if explicit_adapter is not None:
        return explicit_adapter
    if config.working_memory_adapter is not None:
        return config.working_memory_adapter
    if config.working_memory_backend == "llm_assisted":
        if config.working_memory_adapter_mode != ADAPTER_MODE_INERT:
            return build_builtin_working_memory_adapter(config.working_memory_adapter_mode)
        return ClientBackedWorkingMemoryAdapter(
            client_mode=config.working_memory_model_client_mode,
            client_config=config.working_memory_model_client_config or WorkingMemoryModelClientConfig(),
        )
    if config.working_memory_backend == "auto":
        if config.working_memory_adapter_mode != ADAPTER_MODE_INERT:
            return build_builtin_working_memory_adapter(config.working_memory_adapter_mode)
        if config.working_memory_model_client_mode != MODEL_CLIENT_MODE_INERT:
            return ClientBackedWorkingMemoryAdapter(
                client_mode=config.working_memory_model_client_mode,
                client_config=config.working_memory_model_client_config,
            )
        return NullWorkingMemoryAdapter()
    return None


def _working_memory_advisory_source(
    config: RuntimeConfig,
    *,
    resolved_adapter: WorkingMemoryAdapter | None,
    explicit_adapter: WorkingMemoryAdapter | None,
) -> str | None:
    """Return a compact advisory-source label for runtime observability only."""

    if config.working_memory_backend == "local_rule_based":
        return "local_rule_based"
    if config.working_memory_backend == "auto":
        if explicit_adapter is not None or config.working_memory_adapter is not None:
            return "explicit_adapter"
        if isinstance(resolved_adapter, HeuristicWorkingMemoryAdapter):
            return "builtin_heuristic_adapter"
        if isinstance(resolved_adapter, ClientBackedWorkingMemoryAdapter):
            client = getattr(resolved_adapter, "client", None)
            if isinstance(client, AnthropicWorkingMemoryModelClient):
                return "client_backed_anthropic"
            return "client_backed_model_shell"
        if isinstance(resolved_adapter, NullWorkingMemoryAdapter):
            return "auto_no_adapter"
        return "auto"
    if explicit_adapter is not None or config.working_memory_adapter is not None:
        return "explicit_adapter"
    if isinstance(resolved_adapter, HeuristicWorkingMemoryAdapter):
        return "builtin_heuristic_adapter"
    if isinstance(resolved_adapter, ClientBackedWorkingMemoryAdapter):
        client = getattr(resolved_adapter, "client", None)
        if isinstance(client, AnthropicWorkingMemoryModelClient):
            return "client_backed_anthropic"
        return "client_backed_model_shell"
    if isinstance(resolved_adapter, NullWorkingMemoryAdapter):
        return "null_adapter"
    return "llm_assisted"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local runs and verification scenarios."""

    parser = argparse.ArgumentParser(description="Run eva-agent Step 0 runtime")
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--heartbeat-interval", type=float, default=15.0)
    parser.add_argument("--lease-duration", type=float, default=20.0)
    parser.add_argument("--recovering-window", type=float, default=30.0)
    parser.add_argument("--max-ticks", type=int)
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--max-runtime-sec", type=float)
    parser.add_argument("--idle-sleep-sec", type=float, default=0.05)
    parser.add_argument("--turn-guard-window", type=float, default=0.5)
    parser.add_argument("--shallow-patrol-interval", type=float, default=300.0)
    parser.add_argument("--deep-patrol-interval", type=float, default=1800.0)
    parser.add_argument("--full-report-interval", type=float, default=86400.0)
    parser.add_argument("--recent-event-window", type=float, default=1800.0)
    parser.add_argument("--append-only-rotation-max-bytes", type=int)
    parser.add_argument("--append-only-archive-dir-name", default="archive")
    parser.add_argument("--working-memory-backend", choices=["local_rule_based", "auto", "llm_assisted"], default="local_rule_based")
    parser.add_argument("--working-memory-adapter-mode", choices=[ADAPTER_MODE_INERT, ADAPTER_MODE_HEURISTIC], default=ADAPTER_MODE_INERT)
    parser.add_argument(
        "--working-memory-model-client-mode",
        choices=[MODEL_CLIENT_MODE_INERT, MODEL_CLIENT_MODE_HEURISTIC, MODEL_CLIENT_MODE_ANTHROPIC, MODEL_CLIENT_MODE_DEEPSEEK],
        default=MODEL_CLIENT_MODE_ANTHROPIC,
    )
    parser.add_argument("--working-memory-model-client-provider", default=None,
                        help="Provider label (default: derived from mode — 'anthropic' or 'deepseek').")
    parser.add_argument("--working-memory-model-client-model", default=None,
                        help="Model id (default: derived from mode — Anthropic default or DeepSeek default).")
    parser.add_argument("--working-memory-model-client-timeout-sec", type=float, default=5.0)
    parser.add_argument("--inherited-priors-path")
    # Round 1.D: long-run validation snapshot + tripwire CLI options.
    parser.add_argument(
        "--longrun-snapshot-dir",
        default=None,
        help="If set, enable the long-run validation hook: write a stability_profile snapshot every --longrun-hook-interval-sec to this directory. Combined with tripwire options to stop early on invariant violation.",
    )
    parser.add_argument(
        "--longrun-hook-interval-sec",
        type=float,
        default=1800.0,
        help="Interval (seconds) between long-run validation snapshots. Default 1800 (30 min).",
    )
    parser.add_argument(
        "--longrun-tripwire-max-constraint-violation-rate",
        type=float,
        default=0.0,
        help="Long-run tripwire: stop if constraint_violation_rate exceeds this. Default 0.0 (any violation stops). Set to a negative value to disable.",
    )
    parser.add_argument(
        "--longrun-tripwire-min-continuity-score",
        type=float,
        default=0.5,
        help="Long-run tripwire: stop if continuity_preservation_score drops below this. Default 0.5. Set to a negative value to disable.",
    )
    return parser.parse_args()


def build_runtime_config_from_args(args: argparse.Namespace) -> RuntimeConfig:
    """Build one RuntimeConfig from parsed CLI arguments."""

    lifecycle = LifecycleConfig(
        heartbeat_interval_sec=args.heartbeat_interval,
        lease_duration_sec=args.lease_duration,
        recovering_window_sec=args.recovering_window,
        turn_guard_window_sec=args.turn_guard_window,
    )
    external_life = ExternalLifeConfig(
        shallow_patrol_interval_sec=args.shallow_patrol_interval,
        deep_patrol_interval_sec=args.deep_patrol_interval,
        full_report_interval_sec=args.full_report_interval,
        recent_event_window_sec=args.recent_event_window,
    )
    control = LoopControl(
        max_ticks=args.max_ticks,
        max_turns=args.max_turns,
        max_runtime_sec=args.max_runtime_sec,
        idle_sleep_sec=args.idle_sleep_sec,
    )
    append_only_artifacts = AppendOnlyArtifactsConfig(
        rotation_max_bytes=args.append_only_rotation_max_bytes,
        archive_dir_name=args.append_only_archive_dir_name,
    )
    # Derive provider / model defaults from the selected client mode if the
    # user did not override them. This lets ``--working-memory-model-client-mode deepseek``
    # work without forcing the user to also set ``--working-memory-model-client-model``.
    client_mode = args.working_memory_model_client_mode
    if client_mode == MODEL_CLIENT_MODE_DEEPSEEK:
        default_provider = "deepseek"
        default_model = DEFAULT_DEEPSEEK_MODEL
    else:
        default_provider = "anthropic"
        default_model = DEFAULT_ANTHROPIC_MODEL
    resolved_provider = args.working_memory_model_client_provider or default_provider
    resolved_model = args.working_memory_model_client_model or default_model

    return build_runtime_config(
        args.runtime_dir,
        lifecycle=lifecycle,
        external_life=external_life,
        append_only_artifacts=append_only_artifacts,
        control=control,
        working_memory_backend=args.working_memory_backend,
        working_memory_adapter_mode=args.working_memory_adapter_mode,
        working_memory_model_client_mode=args.working_memory_model_client_mode,
        working_memory_model_client_config=WorkingMemoryModelClientConfig(
            provider=resolved_provider,
            model=resolved_model,
            request_timeout_sec=args.working_memory_model_client_timeout_sec,
        ),
        inherited_priors_path=args.inherited_priors_path,
    )



def print_run_summary(summary: RunSummary) -> None:
    """Print the compact runtime summary for CLI callers."""

    print(f"runtime_dir={summary.runtime_dir}")
    print(f"ticks={summary.ticks}")
    print(f"turns={summary.turns}")
    print(f"final_life_state={summary.final_life_state}")
    print(f"instance_valid={summary.instance_valid}")
    print(f"exit_reason={summary.exit_reason}")



def main() -> None:
    """Build runtime config from CLI arguments and print a short summary."""

    args = parse_args()
    config = build_runtime_config_from_args(args)
    summary = run_runtime(config)
    print_run_summary(summary)


if __name__ == "__main__":
    main()
