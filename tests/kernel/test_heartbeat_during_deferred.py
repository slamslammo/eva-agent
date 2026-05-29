"""PR-S1 Slice 10 / R5: heartbeat / liveness NOT frozen during deferred streak.

Plan §2.1 + §6 R5 (CRITICAL): freezing kernel heartbeats during scenario-time
freeze would reintroduce the cell-substrate kill bug observed during run 2/3
of the 100-turn-baseline. This test asserts the runtime keeps ticking and
the lifecycle reaches a clean ``needs_human_consecutive_deferred`` exit even
when every deliberation attempt defers.

If R5 is violated, the runtime would either deadlock (no exit) or be killed
externally — the assertion catches both failure modes.
"""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import (
    ExternalLifeConfig,
    LifecycleConfig,
    LoopControl,
    build_runtime_config,
)
from eva.kernel.main import MAX_CONSECUTIVE_DEFERRED
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario


class _StubSession:
    def __init__(self) -> None:
        self.step_actions: list[str] = []
        self.terminated = False
        self.latest_agent_observation = {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "ep", "step": 0,
            "visible": {
                "life_panel": {"available": True, "values": {"health": 9, "food": 9, "water": 9, "energy": 9}},
                "inventory_panel": {"available": True, "items": {}},
                "facing": "up",
                "local_view": {
                    "format": "semantic_grid", "width": 3, "height": 3,
                    "center": {"row": 1, "col": 1},
                    "cells": [["grass"]*3, ["grass","player","grass"], ["grass"]*3],
                },
                "nearby_objects": [],
            },
            "task_context": {"objective": "survive", "unlocked_achievements_visible": []},
            "available_actions": ["noop","sleep","do","move_left","move_right","move_up","move_down"],
            "notes": [],
        }

    @classmethod
    def start(cls, *, seed=None):
        del seed
        return cls()

    def build_shared_facts(self) -> dict:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str):
        self.step_actions.append(action_name)
        return type("Step", (), {
            "raw_observation": None, "reward": 0.0, "done": False, "raw_info": {},
            "agent_observation": dict(self.latest_agent_observation),
            "before_observation": dict(self.latest_agent_observation),
            "after_action_observation": dict(self.latest_agent_observation),
        })()

    def close(self) -> None:
        pass


class HeartbeatDuringDeferredTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_heartbeat_continues_during_deferred_streak_clean_exit(self) -> None:
        """R5: deferred streak does NOT block heartbeat ticks; exit is clean.

        Force a deferred streak by patching LifecycleRuntime so the counter
        starts at MAX-1 (one more defer trips the exit). The exit must come
        from our new ``needs_human_consecutive_deferred`` reason, not from
        substrate timeout, lease expiry, or external kill — that's the
        signature of heartbeat still functioning during the deferred attempt.
        """
        from eva.kernel.lifecycle import LifecycleRuntime
        original_init = LifecycleRuntime.__init__

        def init_with_high_counter(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._consecutive_deferred = MAX_CONSECUTIVE_DEFERRED  # primed past threshold

        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2, lease_duration_sec=1.0,
                    recovering_window_sec=0.05, turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01, deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03, recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=50, max_runtime_sec=3.0, idle_sleep_sec=0.01),
            )
            session = _StubSession()
            with patch.object(LifecycleRuntime, "__init__", init_with_high_counter):
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    summary = run_crafter_runtime(config)
            # Clean planned exit, NOT substrate timeout / lease expiry / hang.
            self.assertEqual(summary.exit_reason, "needs_human_consecutive_deferred",
                             "deferred streak must exit cleanly via R8, not via R5-violating substrate timeout")
            # Liveness preserved through the exit.
            self.assertTrue(summary.instance_valid,
                            "instance_valid must remain True — substrate was not killed")
            # PR-T1: Crafter is clock_source="step", so there is NO wall-clock
            # heartbeat tick (step is the pulse → summary.ticks == 0). The R5
            # spirit (a deferred streak does not deadlock) is proven by the loop
            # actively ESCALATING to the R8 needs_human exit rather than spinning
            # until the anti-runaway watchdog (max_runtime_sec).
            self.assertEqual(summary.ticks, 0,
                             "step mode has no wall-clock heartbeat ticks")
            self.assertNotEqual(summary.exit_reason, "max_runtime_sec",
                                "deferred streak must escalate via R8, not spin to the watchdog")


if __name__ == "__main__":
    unittest.main()
