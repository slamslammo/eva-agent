"""Round 1.D-1 / D-2: pin graceful interrupt + periodic hook behavior on
``run_runtime``.

Pre-fix:
- KeyboardInterrupt during the runtime loop short-circuits without writing
  the shutdown event. ``finally`` releases the instance guard but never
  records that the run actually ended.
- There is no callback mechanism for periodic in-loop work (snapshots,
  tripwires) — only the max-* bounds can stop the loop.

Post-fix:
- ``run_runtime`` wraps the loop in ``try / except KeyboardInterrupt``;
  shutdown event is always written before returning.
- ``RunSummary`` gains an ``exit_reason`` string field reporting why the
  loop exited (``"normal"``, ``"max_ticks"``, ``"max_turns"``,
  ``"max_runtime_sec"``, ``"keyboard_interrupt"``, or
  ``"periodic_hook_stop"`` plus a reason suffix).
- ``run_runtime`` accepts ``periodic_hook`` and ``hook_interval_sec`` for
  in-loop scheduled callbacks that can also short-circuit the loop.
"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from eva.kernel import StateStore, build_runtime_paths
from eva.kernel.config import (
    AppendOnlyArtifactsConfig,
    ExternalLifeConfig,
    LifecycleConfig,
    LoopControl,
    RuntimeConfig,
)
from eva.kernel.main import RunSummary, run_runtime
from scenarios.linux_runtime import activate_linux_runtime_scenario


def _bounded_config(temp_dir: str, *, max_runtime_sec: float | None = None, max_ticks: int | None = None) -> RuntimeConfig:
    paths = build_runtime_paths(temp_dir)
    return RuntimeConfig(
        paths=paths,
        lifecycle=LifecycleConfig(
            heartbeat_interval_sec=0.05,
            recovering_window_sec=0.01,
            turn_guard_window_sec=0.005,
        ),
        external_life=ExternalLifeConfig(
            shallow_patrol_interval_sec=0.005,
            deep_patrol_interval_sec=0.01,
            full_report_interval_sec=0.02,
        ),
        control=LoopControl(
            max_ticks=max_ticks,
            max_turns=None,
            max_runtime_sec=max_runtime_sec,
            idle_sleep_sec=0.005,
        ),
        working_memory_backend="local_rule_based",
        append_only_artifacts=AppendOnlyArtifactsConfig(),
    )


class RunSummaryExitReasonTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_runsummary_has_exit_reason_field(self) -> None:
        """Round 1.D-1: ``RunSummary`` must expose an ``exit_reason`` field."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_ticks=2)
            summary = run_runtime(config)
            self.assertTrue(hasattr(summary, "exit_reason"))
            self.assertIsInstance(summary.exit_reason, str)

    def test_max_ticks_exit_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_ticks=2)
            summary = run_runtime(config)
            self.assertEqual(summary.exit_reason, "max_ticks")

    def test_max_runtime_sec_exit_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_runtime_sec=0.15)
            summary = run_runtime(config)
            self.assertEqual(summary.exit_reason, "max_runtime_sec")


class GracefulInterruptTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_keyboard_interrupt_writes_shutdown_event(self) -> None:
        """Round 1.D-1: KeyboardInterrupt during the loop must still write
        the shutdown event so the trace has a clean termination record."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_ticks=100)

            # Patch ``time.sleep`` inside the eva.kernel.main module so the
            # first call raises KeyboardInterrupt. This simulates Ctrl+C
            # arriving mid-loop without flakiness.
            call_count = {"n": 0}
            real_sleep = time.sleep

            def interrupting_sleep(duration: float) -> None:
                call_count["n"] += 1
                if call_count["n"] >= 2:
                    raise KeyboardInterrupt()
                real_sleep(min(duration, 0.001))

            with mock.patch("eva.kernel.main.time.sleep", side_effect=interrupting_sleep):
                summary = run_runtime(config)

            self.assertEqual(summary.exit_reason, "keyboard_interrupt")

            # Shutdown event must be in events.jsonl.
            store = StateStore(config.paths)
            events = store.read_events()
            event_types = [e.get("event_type") for e in events]
            self.assertIn("shutdown", event_types)


class PeriodicHookTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_periodic_hook_fires_at_least_once_during_run(self) -> None:
        """Round 1.D-2: a periodic_hook with short interval must fire."""

        calls: list[dict] = []

        def hook(*, runtime_dir, elapsed_since_start, ticks, turns):
            calls.append({
                "runtime_dir": runtime_dir,
                "elapsed_since_start": elapsed_since_start,
                "ticks": ticks,
                "turns": turns,
            })
            return False, None

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_runtime_sec=0.5)
            summary = run_runtime(config, periodic_hook=hook, hook_interval_sec=0.05)
            self.assertGreater(len(calls), 0, "Hook must have fired at least once")
            self.assertEqual(summary.exit_reason, "max_runtime_sec")

    def test_periodic_hook_can_stop_the_loop(self) -> None:
        """Round 1.D-2: hook returning ``(True, reason)`` must short-circuit
        the loop and set ``exit_reason`` accordingly."""

        def stopping_hook(*, runtime_dir, elapsed_since_start, ticks, turns):
            return True, "tripwire:test_stop"

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_runtime_sec=10.0)  # generous; hook should stop us first
            summary = run_runtime(config, periodic_hook=stopping_hook, hook_interval_sec=0.05)
            self.assertEqual(summary.exit_reason, "tripwire:test_stop")

    def test_periodic_hook_error_does_not_crash_loop(self) -> None:
        """Round 1.D-2 defensive: a buggy hook must not crash the long-run."""

        def buggy_hook(*, runtime_dir, elapsed_since_start, ticks, turns):
            raise RuntimeError("buggy hook")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_runtime_sec=0.3)
            summary = run_runtime(config, periodic_hook=buggy_hook, hook_interval_sec=0.05)
            self.assertEqual(summary.exit_reason, "max_runtime_sec")

    def test_no_hook_default_behavior_unchanged(self) -> None:
        """Linux equivalence: without ``periodic_hook``, behavior matches the
        pre-Round-1.D path exactly except for the new ``exit_reason`` field."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _bounded_config(temp_dir, max_ticks=3)
            summary = run_runtime(config)
            self.assertEqual(summary.exit_reason, "max_ticks")
            self.assertEqual(summary.ticks, 3)


if __name__ == "__main__":
    unittest.main()
