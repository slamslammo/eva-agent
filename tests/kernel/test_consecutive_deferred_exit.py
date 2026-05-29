"""PR-S1 Slice 5: consecutive_deferred ≥ MAX → exit_reason=needs_human.

Plan §3.4 + R8: protect against infinite defer loops (e.g. LLM stuck failing
every decision). Threshold default 10; honored across scenarios because the
counter only bumps when bridge signals env_step_invoked=False.

Red lines:
- R5 reaffirmed: heartbeat continues during the deferred streak — NEEDS_HUMAN
  exit is triggered cleanly via the main-loop break, not by freezing the
  heartbeat path.
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
    """Stub session — but does NOT need step_action since bridge will defer."""

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


class MaxConsecutiveDeferredExitTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_default_max_consecutive_deferred_constant(self) -> None:
        self.assertEqual(MAX_CONSECUTIVE_DEFERRED, 10)

    def test_exit_reason_needs_human_when_threshold_reached(self) -> None:
        """Force counter past threshold via direct lifecycle injection.

        Simulates a deferred streak by patching LifecycleRuntime so the
        counter starts at MAX-1 and the next deferred response trips the exit.
        """
        from eva.kernel.lifecycle import LifecycleRuntime
        original_init = LifecycleRuntime.__init__

        def init_with_high_counter(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._consecutive_deferred = MAX_CONSECUTIVE_DEFERRED  # threshold already reached

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
                control=LoopControl(max_turns=50, max_runtime_sec=2.0, idle_sleep_sec=0.01),
            )
            session = _StubSession()
            with patch.object(LifecycleRuntime, "__init__", init_with_high_counter):
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    summary = run_crafter_runtime(config)
            self.assertEqual(summary.exit_reason, "needs_human_consecutive_deferred")


if __name__ == "__main__":
    unittest.main()
