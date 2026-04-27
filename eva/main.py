"""CLI entrypoint and bounded runtime loop for eva-agent."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from .kernel import (
    EventRecord,
    ExternalLifeConfig,
    InstanceGuard,
    LifecycleConfig,
    LoopControl,
    RuntimeConfig,
    StateStore,
    build_runtime_config,
    emit_log_line,
    utc_now,
)
from .lifecycle import LifecycleRuntime


@dataclass
class RunSummary:
    """High-level summary returned after one runtime execution."""

    ticks: int
    turns: int
    final_life_state: str
    instance_valid: bool
    runtime_dir: str


def run_runtime(config: RuntimeConfig) -> RunSummary:
    """Run the lifecycle loop until one of the configured bounds is reached."""

    store = StateStore(config.paths)
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

    runtime = LifecycleRuntime(store, instance_guard, config.lifecycle, config.external_life)
    next_heartbeat_at = utc_now()
    started_at = time.monotonic()
    ticks = 0
    turns = 0

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
                # Sleep only until the next heartbeat boundary when there is no queued work.
                sleep_for = min(config.control.idle_sleep_sec, max((next_heartbeat_at - now).total_seconds(), 0.0))
                time.sleep(sleep_for)

            if config.control.max_ticks is not None and ticks >= config.control.max_ticks:
                break
            if config.control.max_turns is not None and turns >= config.control.max_turns:
                break
            if config.control.max_runtime_sec is not None and (time.monotonic() - started_at) >= config.control.max_runtime_sec:
                break

        final_state = store.read_runtime_state()
        store.append_event(EventRecord(event_type="shutdown", timestamp=utc_now(), instance_id=active_record.instance_id, generation=active_record.generation, life_state=final_state.life_state, details={"ticks": ticks, "turns": turns}))
        emit_log_line("shutdown", instance=active_record.instance_id, generation=active_record.generation, state=final_state.life_state, ticks=ticks, turns=turns, instance_valid=final_state.instance_valid)
        return RunSummary(
            ticks=ticks,
            turns=turns,
            final_life_state=final_state.life_state,
            instance_valid=final_state.instance_valid,
            runtime_dir=str(config.paths.runtime_dir),
        )
    finally:
        instance_guard.release()


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
    return parser.parse_args()


def main() -> None:
    """Build runtime config from CLI arguments and print a short summary."""

    args = parse_args()
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
    config = build_runtime_config(args.runtime_dir, lifecycle=lifecycle, external_life=external_life, control=control)
    summary = run_runtime(config)
    print(f"runtime_dir={summary.runtime_dir}")
    print(f"ticks={summary.ticks}")
    print(f"turns={summary.turns}")
    print(f"final_life_state={summary.final_life_state}")
    print(f"instance_valid={summary.instance_valid}")


if __name__ == "__main__":
    main()
