"""PR-S1 gate fix (CHANGES_REQUESTED 2026-05-29): clock_source is LOAD-BEARING.

A's gate review: in commit 9049106 ``clock_source`` was decorative — it lived
only in comments and the ``main.py`` run_meta record. The actual scenario-step
accounting branched on the bridge's ``env_step_invoked`` flag, never on the
field. Per blueprint §2.7 the *kernel* (not the scenario bridge) must read
``clock_source`` to choose its cadence source; embedding step semantics in the
Crafter bridge alone is a forbidden per-scenario cadence fork.

These tests pin the field as load-bearing:
- the kernel reads ``clock_source`` from the active existence semantics at
  construction (wiring: crafter→"step", linux→"wall_clock");
- under ``wall_clock`` the kernel ENFORCES the attempt==scenario_step invariant
  even if a bridge wrongly sets ``env_step_invoked=False`` (A's counter-example
  — a future wall_clock scenario can never silently skip via a bridge bug);
- under ``step`` the kernel honors the bridge defer signal (divergence path).

The divergence/invariant assertions call the REAL counter method
``_update_scenario_counters`` so the logic cannot drift behind an inline copy.
"""

from __future__ import annotations

import tempfile
import unittest

from eva.kernel import (
    LifecycleConfig,
    StateStore,
    build_runtime_paths,
)
from eva.kernel.instance import InstanceGuard
from eva.kernel.lifecycle import LifecycleRuntime
from scenarios.crafter import activate_crafter_scenario
from scenarios.linux_runtime import activate_linux_runtime_scenario


def _build_runtime(temp_dir: str) -> LifecycleRuntime:
    paths = build_runtime_paths(temp_dir)
    store = StateStore(paths)
    guard = InstanceGuard(paths.runtime_dir / "eva.lock", store, LifecycleConfig())
    return LifecycleRuntime(store, guard, LifecycleConfig())


class ClockSourceWiringTests(unittest.TestCase):
    """The kernel reads clock_source from the active existence semantics."""

    def test_crafter_runtime_reads_step_clock_source(self) -> None:
        activate_crafter_scenario()
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = _build_runtime(temp_dir)
            self.assertEqual(
                runtime._clock_source, "step",
                "Crafter declares clock_source='step'; kernel must read it",
            )

    def test_linux_runtime_reads_wall_clock_source(self) -> None:
        activate_linux_runtime_scenario()
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = _build_runtime(temp_dir)
            self.assertEqual(
                runtime._clock_source, "wall_clock",
                "Linux declares clock_source='wall_clock'; kernel must read it",
            )


class WallClockInvariantTests(unittest.TestCase):
    """A's counter-example: wall_clock kernel ignores a wrongly-set defer flag."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_wall_clock_forces_scenario_step_despite_bridge_defer(self) -> None:
        """Under wall_clock, attempt==scenario_step holds even if bridge defers.

        This is the load-bearing proof: the kernel does NOT trust a bridge's
        ``env_step_invoked=False`` under wall_clock — it enforces the Linux
        invariant from the field, not from the bridge never setting the flag.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = _build_runtime(temp_dir)
            runtime._clock_source = "wall_clock"  # simulate a wall_clock scenario
            # Bridge WRONGLY signals a defer; kernel must ignore it.
            deferred_summary = {"env_step_invoked": False, "selected_action": "x"}
            for _ in range(5):
                runtime._update_scenario_counters(deferred_summary)
            self.assertEqual(runtime._attempt_index, 5)
            self.assertEqual(
                runtime._scenario_step_index, 5,
                "wall_clock: kernel forces scenario_step regardless of bridge defer",
            )
            self.assertEqual(
                runtime._consecutive_deferred, 0,
                "wall_clock: deferred guard must never accumulate",
            )

    def test_step_honors_bridge_defer_signal(self) -> None:
        """Under step, the kernel honors env_step_invoked=False (divergence)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = _build_runtime(temp_dir)
            runtime._clock_source = "step"
            deferred_summary = {"env_step_invoked": False, "selected_action": "noop"}
            for _ in range(3):
                runtime._update_scenario_counters(deferred_summary)
            self.assertEqual(runtime._attempt_index, 3)
            self.assertEqual(
                runtime._scenario_step_index, 0,
                "step: deferred attempts must NOT advance scenario_step",
            )
            self.assertEqual(runtime._consecutive_deferred, 3)
            # An executable turn resets the streak and advances scenario_step.
            runtime._update_scenario_counters({"env_step_invoked": True, "selected_action": "do"})
            self.assertEqual(runtime._attempt_index, 4)
            self.assertEqual(runtime._scenario_step_index, 1)
            self.assertEqual(runtime._consecutive_deferred, 0)


if __name__ == "__main__":
    unittest.main()
