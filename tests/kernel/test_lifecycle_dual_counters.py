"""PR-S1 Slice 4: lifecycle dual counters (attempt_index / scenario_step_index).

Plan §3.1: kernel tracks two indices per scenario clock_source:
- ``attempt_index`` bumps on every decision attempt (success or defer)
- ``scenario_step_index`` bumps only when env.step was invoked (mediated executable action)

Red lines:
- R6: scenario_step_index advancement bound to mediated executable action only
- R7: failed attempts visible (attempt_index increments anyway)
"""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import (
    ExternalLifeConfig,
    LifecycleConfig,
    LoopControl,
    build_runtime_config,
)
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


class _StubSession:
    def __init__(self) -> None:
        self.step_actions: list[str] = []
        self.terminated = False
        self.latest_agent_observation = {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "ep",
            "step": 0,
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


def _run_config(temp_dir: str):
    return build_runtime_config(
        temp_dir,
        lifecycle=LifecycleConfig(
            heartbeat_interval_sec=0.2, lease_duration_sec=1.0,
            recovering_window_sec=0.05, turn_guard_window_sec=0.01,
        ),
        external_life=ExternalLifeConfig(
            shallow_patrol_interval_sec=0.01, deep_patrol_interval_sec=0.02,
            full_report_interval_sec=0.03, recent_event_window_sec=60.0,
        ),
        control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
    )


class _CounterCapturingRuntime:
    """Wrap LifecycleRuntime so we can read its counters after a run."""

    captured: dict = {}

    @classmethod
    def capture(cls, runtime):
        cls.captured["attempt"] = runtime._attempt_index
        cls.captured["scenario_step"] = runtime._scenario_step_index
        cls.captured["consecutive_deferred"] = runtime._consecutive_deferred


class DualCountersInitTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_counters_start_at_zero(self) -> None:
        """Counters are zero at runtime construction (mode-independent invariant).

        PR-T1: under clock_source="step" the step loop deliberates on the very
        first step (there are no maintenance-only turns to observe), so the
        previous end-to-end "2 maintenance turns keep counters 0" premise no
        longer holds. The genuine 'start at zero' invariant is checked directly
        at construction, before any step / turn runs — identical in both modes.
        """
        from eva.kernel.lifecycle import LifecycleRuntime
        from eva.kernel import StateStore, build_runtime_paths
        from eva.kernel.instance import InstanceGuard

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_runtime_paths(temp_dir)
            store = StateStore(paths)
            guard = InstanceGuard(paths.runtime_dir / "eva.lock", store, LifecycleConfig())
            runtime = LifecycleRuntime(store, guard, LifecycleConfig())
            self.assertEqual(runtime._attempt_index, 0)
            self.assertEqual(runtime._scenario_step_index, 0)
            self.assertEqual(runtime._consecutive_deferred, 0)


class DualCountersAdvanceTests(unittest.TestCase):
    """End-to-end: with stub producer emitting raw actions, both counters advance together."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_both_counters_advance_when_env_step_invoked(self) -> None:
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "stub"}]}),
            observation_fn=lambda: _StubSession.start().latest_agent_observation,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            session = _StubSession()
            producer._observation_fn = lambda: session.latest_agent_observation

            # Patch LifecycleRuntime to capture counters after run.
            from eva.kernel.lifecycle import LifecycleRuntime
            original_init = LifecycleRuntime.__init__

            captured_runtime = []

            def capturing_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                captured_runtime.append(self)

            with patch.object(LifecycleRuntime, "__init__", capturing_init):
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    run_crafter_runtime(config, candidate_producer=producer)

            self.assertGreaterEqual(len(captured_runtime), 1)
            rt = captured_runtime[0]
            # With non-deferred releases, attempt == scenario_step.
            self.assertGreaterEqual(rt._attempt_index, 1)
            self.assertEqual(rt._attempt_index, rt._scenario_step_index,
                             "non-deferred turns: attempt should equal scenario_step")
            self.assertEqual(rt._consecutive_deferred, 0)

    def test_deferred_response_summary_bumps_consecutive_but_not_scenario_step(self) -> None:
        """Unit-level: feed a deferred response_summary to the REAL counter method.

        This bypasses the end-to-end mediator/bridge path (which sometimes
        emits real actions via heuristic candidates) but exercises the actual
        kernel logic via ``_update_scenario_counters`` — no inline copy that
        could drift behind the production code (the gate-fix lesson). Crafter
        is active (setUp) so ``_clock_source == "step"`` and the bridge's
        ``env_step_invoked`` signal is honored.
        """
        from eva.kernel.lifecycle import LifecycleRuntime
        from eva.kernel import StateStore, build_runtime_paths
        from eva.kernel.instance import InstanceGuard

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_runtime_paths(temp_dir)
            store = StateStore(paths)
            guard = InstanceGuard(paths.eva_lock_file if hasattr(paths, 'eva_lock_file') else paths.runtime_dir / "eva.lock", store, LifecycleConfig())
            runtime = LifecycleRuntime(store, guard, LifecycleConfig())
            self.assertEqual(runtime._clock_source, "step")
            self.assertEqual(runtime._scenario_step_index, 0)
            self.assertEqual(runtime._consecutive_deferred, 0)

            # deferred response_summary has env_step_invoked=False.
            deferred_summary = {"env_step_invoked": False, "selected_action": "noop"}
            for _ in range(3):
                runtime._update_scenario_counters(deferred_summary)

            self.assertEqual(runtime._attempt_index, 3)
            self.assertEqual(runtime._scenario_step_index, 0,
                             "deferred: scenario_step must NOT advance")
            self.assertEqual(runtime._consecutive_deferred, 3)

            # Then an executable turn arrives — both bump, consecutive resets.
            runtime._update_scenario_counters({"env_step_invoked": True, "selected_action": "do"})
            self.assertEqual(runtime._attempt_index, 4)
            self.assertEqual(runtime._scenario_step_index, 1)
            self.assertEqual(runtime._consecutive_deferred, 0)


if __name__ == "__main__":
    unittest.main()
