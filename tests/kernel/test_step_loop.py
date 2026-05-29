"""PR-T1 slice 2/3: clock_source=step drives the clean step loop (no wall-clock).

Plan rev3 §4 + G1 §2: under clock_source="step" (Crafter) the kernel runs a
step-driven main loop — step is the pulse, no wall-clock heartbeat tick / lease
renewal / heartbeat-deadline yield. scenario_step advances only on a mediated
env.step; budget is max_steps.

RED before slice 2/3: Crafter currently falls through to _run_wall_clock_loop
(slice 1 extracted it but added no branch), so the run exits "max_turns" with
wall-clock heartbeat ticks + possible heartbeat_deadline_near yields.

GREEN after: run_runtime branches on clock_source; step mode exits "max_steps",
emits zero heartbeat_deadline_near events, and scenario_step tracks env.step.
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


def _step_producer(session: _StubSession) -> CrafterLLMActionProducer:
    producer = CrafterLLMActionProducer(
        chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "stub"}]}),
        observation_fn=lambda: session.latest_agent_observation,
    )
    producer._observation_fn = lambda: session.latest_agent_observation
    return producer


class StepLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_step_mode_exits_max_steps_with_no_yield(self) -> None:
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
                control=LoopControl(max_turns=3, max_runtime_sec=5.0, idle_sleep_sec=0.01),
            )
            session = _StubSession()
            producer = _step_producer(session)
            with patch.object(CrafterRuntimeSession, "start", return_value=session):
                summary = run_crafter_runtime(config, candidate_producer=producer)

            # Step mode budget is max_steps (== env.step count), not wall-clock max_turns.
            self.assertEqual(summary.exit_reason, "max_steps")
            # scenario_step advanced on mediated env.step.
            self.assertGreaterEqual(summary.scenario_step_count, 1)
            # The clean step loop never emits a heartbeat-deadline yield.
            events_path = f"{temp_dir}/events.jsonl"
            yields = 0
            with open(events_path, encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    if record.get("details", {}).get("reason") == "heartbeat_deadline_near":
                        yields += 1
            self.assertEqual(yields, 0, "step mode must not yield to a wall-clock heartbeat")

    def test_step_mode_env_done_ends_individual(self) -> None:
        """R-a: env reporting done (embodied death) ends the individual.

        rev2 always ended at max_turns (the agent never died), so the
        death -> individual_terminated path was untested. Under step mode the
        loop must catch env done after a stepped action and exit
        ``individual_terminated`` (one Crafter life = one individual), not run on
        to max_steps. The next run is a fresh individual (run-level continuity).
        """
        class _TerminatingSession(_StubSession):
            def step_action(self, action_name: str):
                result = super().step_action(action_name)
                self.terminated = True  # env returns done after this step (e.g. HP=0)
                return result

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
                control=LoopControl(max_turns=20, max_runtime_sec=5.0, idle_sleep_sec=0.01),
            )
            session = _TerminatingSession()
            producer = _step_producer(session)
            with patch.object(CrafterRuntimeSession, "start", return_value=session):
                summary = run_crafter_runtime(config, candidate_producer=producer)

            self.assertEqual(summary.exit_reason, "individual_terminated",
                             "env done must end the individual, not run to max_steps")
            # Death happened on the first stepped action, far short of max_steps=20.
            self.assertGreaterEqual(summary.scenario_step_count, 1)
            self.assertLess(summary.scenario_step_count, 20)

    def test_step_mode_persists_counts_to_artifact(self) -> None:
        """§6 #5 / Q3: scenario_step + attempt counts land in the append-only

        artifact (the rev2 audit gap was that these were not greppable). The
        step-loop shutdown event must carry scenario_step_index + attempt_index.
        """
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
                control=LoopControl(max_turns=3, max_runtime_sec=5.0, idle_sleep_sec=0.01),
            )
            session = _StubSession()
            producer = _step_producer(session)
            with patch.object(CrafterRuntimeSession, "start", return_value=session):
                summary = run_crafter_runtime(config, candidate_producer=producer)

            shutdown = None
            with open(f"{temp_dir}/events.jsonl", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    if record.get("event_type") == "shutdown":
                        shutdown = record
            self.assertIsNotNone(shutdown, "a shutdown event must be persisted")
            self.assertIn("scenario_step_index", shutdown["details"])
            self.assertIn("attempt_index", shutdown["details"])
            self.assertEqual(shutdown["details"]["clock_source"], "step")
            # Counts in the artifact match the in-memory RunSummary.
            self.assertEqual(shutdown["details"]["scenario_step_index"], summary.scenario_step_count)


if __name__ == "__main__":
    unittest.main()
