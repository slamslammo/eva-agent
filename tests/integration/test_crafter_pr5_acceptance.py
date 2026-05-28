"""PR-5 acceptance tests — single-chain integration (stub LLM).

Covers §9.2 acceptance criteria verifiable without a live LLM:
  AC-1  water=2 → A'(s) restricted to movement set before LLM call (§9.2 ①)
  AC-3  stub LLM output action is within A'(s) (§9.2 ③)
  AC-6  bridge executes the action without rewriting it (§9.2 ⑥)
  AC-7  LLM unavailable → fallback=defer, no baseline action (§9.2 ⑦)

AC-4/AC-5 (water tile navigation with real Crafter env + real LLM) require
EVA_LLM_* env vars and are exercised in the live short-run script.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import ExternalLifeConfig, LifecycleConfig, LoopControl, build_runtime_config
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


def _water_critical_obs(water: int = 2, water_visible: bool = True) -> dict:
    if water_visible:
        cells = [
            ["grass", "water", "grass"],
            ["grass", "player", "grass"],
            ["grass", "grass", "grass"],
        ]
    else:
        cells = [
            ["grass", "grass", "grass"],
            ["grass", "player", "grass"],
            ["grass", "grass", "grass"],
        ]
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": "ep-water-test",
        "step": 1,
        "visible": {
            "life_panel": {
                "available": True,
                "values": {"health": 8, "food": 7, "water": water, "energy": 7},
            },
            "inventory_panel": {"available": True, "items": {}},
            "facing": "up",
            "local_view": {
                "format": "semantic_grid",
                "width": 3,
                "height": 3,
                "center": {"row": 1, "col": 1},
                "cells": cells,
            },
            "nearby_objects": [],
        },
        "task_context": {
            "objective": "survive",
            "unlocked_achievements_visible": [],
        },
        "available_actions": ["noop", "sleep", "do", "move_left", "move_right", "move_up", "move_down"],
        "notes": [],
    }


class _WaterCriticalStubSession:
    def __init__(self, water: int = 2, water_visible: bool = True) -> None:
        self.step_actions: list[str] = []
        self.latest_agent_observation = _water_critical_obs(water=water, water_visible=water_visible)
        self.terminated = False

    @classmethod
    def start(cls, *, seed=None) -> "_WaterCriticalStubSession":
        del seed
        return cls()

    def build_shared_facts(self) -> dict:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str):
        self.step_actions.append(action_name)
        # After a move action, simulate water replenishment (walked into water tile).
        new_water = min(9, self.latest_agent_observation["visible"]["life_panel"]["values"]["water"] + 2)
        after = _water_critical_obs(water=new_water, water_visible=False)
        self.latest_agent_observation = after
        return type("Step", (), {
            "raw_observation": None,
            "reward": 0.0,
            "done": False,
            "raw_info": {},
            "agent_observation": after,
            "before_observation": dict(self.latest_agent_observation),
            "after_action_observation": after,
        })()

    def close(self) -> None:
        pass


def _movement_stub_producer(chosen_action: str = "move_up") -> CrafterLLMActionProducer:
    def _chat(messages):
        return json.dumps({"candidates": [{"action": chosen_action, "reason": "moving toward water"}]})

    obs_holder: dict = {}

    def _obs():
        return obs_holder.get("latest", _water_critical_obs())

    p = CrafterLLMActionProducer(chat_fn=_chat, observation_fn=_obs)
    return p


def _run_config(temp_dir: str):
    return build_runtime_config(
        temp_dir,
        lifecycle=LifecycleConfig(
            heartbeat_interval_sec=0.2,
            lease_duration_sec=1.0,
            recovering_window_sec=0.05,
            turn_guard_window_sec=0.01,
        ),
        external_life=ExternalLifeConfig(
            shallow_patrol_interval_sec=0.01,
            deep_patrol_interval_sec=0.02,
            full_report_interval_sec=0.03,
            recent_event_window_sec=60.0,
        ),
        control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
    )


class CrafterAC1AnchorRestrictionTests(unittest.TestCase):
    """AC-1: water=2 → A'(s) restricted to movement set before LLM call."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_water_critical_anchor_excludes_noop_sleep_do(self) -> None:
        from eva.l3_deliberation.contracts import build_deliberation_input
        from eva.anchor import build_action_domain
        from scenarios.crafter.anchors import build_crafter_action_domain

        di = build_deliberation_input(
            {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
            {
                "top_drive": "metabolic",
                "drive_levels": {
                    "acquisition": 0.3,
                    "metabolic": 0.9,
                    "safety": 0.2,
                    "recovery": 0.2,
                    "capability": 0.1,
                    "exploration": 0.1,
                },
                "drive_trends": {"metabolic": "worsening"},
            },
            {
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        obs = _water_critical_obs(water=2, water_visible=True)
        agent_state = build_action_domain(di).agent_state
        domain = build_crafter_action_domain(agent_state, obs)

        self.assertNotIn("noop", domain.action_set, "noop must be excluded when water=2")
        self.assertNotIn("sleep", domain.action_set, "sleep must be excluded when water=2")
        self.assertNotIn("do", domain.action_set, "do must be excluded when water=2 (not facing water object)")
        move_actions = {"move_left", "move_right", "move_up", "move_down"}
        self.assertTrue(domain.action_set.issubset(move_actions), f"A'(s)={domain.action_set!r} must be subset of move actions")
        self.assertIn("water_critical_move_set", domain.restriction_reasons)


class CrafterAC3AC6WaterChainIntegrationTests(unittest.TestCase):
    """AC-3 + AC-6: stub LLM move action within A'(s) is executed without bridge rewriting."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_stub_move_action_executed_as_raw_action(self) -> None:
        chosen = "move_up"
        producer = _movement_stub_producer(chosen)

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            stub_session = _WaterCriticalStubSession(water=2, water_visible=True)
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config, candidate_producer=producer)
            from eva.kernel import StateStore
            store = StateStore(config.paths)
            history = store.read_response_history()
            self.assertGreaterEqual(len(history), 1)

            raw_executed = [r for r in history if r.get("selected_action_reason") == "crafter_raw_action_execution"]
            self.assertGreaterEqual(len(raw_executed), 1, "At least one raw-action execution expected")
            for record in raw_executed:
                # AC-6: bridge executes exactly the action from release_context, not a rewritten one.
                self.assertEqual(record.get("selected_action"), chosen, "Bridge must not rewrite the LLM-selected action")

    def test_move_actions_in_movement_set_are_accepted(self) -> None:
        for action in ("move_left", "move_right", "move_up", "move_down"):
            producer = _movement_stub_producer(action)
            with tempfile.TemporaryDirectory() as temp_dir:
                config = _run_config(temp_dir)
                stub_session = _WaterCriticalStubSession(water=2, water_visible=True)
                with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                    run_crafter_runtime(config, candidate_producer=producer)
                from eva.kernel import StateStore
                store = StateStore(config.paths)
                history = store.read_response_history()
                raw_executed = [r for r in history if r.get("selected_action_reason") == "crafter_raw_action_execution"]
                if raw_executed:
                    self.assertEqual(raw_executed[0].get("selected_action"), action)


class CrafterAC7FallbackDeferTests(unittest.TestCase):
    """AC-7: LLM unavailable → fallback=defer, no baseline action introduced."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_no_llm_producer_all_responses_are_defer_or_raw_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            stub_session = _WaterCriticalStubSession(water=2, water_visible=True)
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config)
            from eva.kernel import StateStore
            store = StateStore(config.paths)
            history = store.read_response_history()
            self.assertGreaterEqual(len(history), 1)
            for record in history:
                self.assertIn(
                    record.get("selected_action_reason"),
                    {"crafter_bridge_defer_no_raw_action", "crafter_raw_action_execution"},
                    f"Unexpected reason: {record.get('selected_action_reason')!r}",
                )

    def test_chat_fn_none_producer_default_inhibition(self) -> None:
        # When chat_fn=None, produce() returns []. Empty candidates → mediator withholds
        # → bridge not called → no step_action taken. This is v0.5 default inhibition.
        # (Distinct from fallback=defer, which requires the bridge to be called with no hint.)
        producer = CrafterLLMActionProducer(
            chat_fn=None,
            observation_fn=lambda: _water_critical_obs(water=2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            stub_session = _WaterCriticalStubSession(water=2, water_visible=True)
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config, candidate_producer=producer)
            # With chat_fn=None → empty candidates → mediator withholds → no step_action.
            # No baseline controller is invoked — this is default inhibition, not fallback=defer.
            for action in stub_session.step_actions:
                # If any step happened (e.g. from an earlier heuristic turn before producer,
                # or emergency path), it must not be an invented non-noop baseline action.
                self.assertIn(action, {"noop", "sleep"}, f"Unexpected action {action!r} from default-inhibition path")


class CrafterSingleChainTraceTests(unittest.TestCase):
    """§9.5 single-chain trace: verify the causal chain emits the right transforms."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_water_chain_trace_contains_expected_transforms(self) -> None:
        import json
        import os
        from pathlib import Path

        chosen = "move_up"
        producer = _movement_stub_producer(chosen)
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            stub_session = _WaterCriticalStubSession(water=2, water_visible=True)
            with patch.dict(os.environ, {"EVA_TRACE": "1"}), patch.object(
                CrafterRuntimeSession, "start", return_value=stub_session
            ):
                run_crafter_runtime(config, candidate_producer=producer)

            runtime_dir = Path(config.paths.runtime_dir)
            trace_path = runtime_dir / "cognitive_trace.jsonl"
            self.assertTrue(trace_path.exists(), "Trace file must be created")
            records = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
            transform_ids = {r["transform_id"] for r in records if r["event_type"] == "transform"}

            # §9.5 chain must be traceable.
            for expected in ("anchor.admit", "l3.candidate_produce", "l3.decide_release", "bridge.resolve_action"):
                self.assertIn(expected, transform_ids, f"Expected transform '{expected}' in trace")

            # bridge.resolve_action must carry a non-None selected_action_reason.
            bridge_events = [r for r in records if r.get("transform_id") == "bridge.resolve_action"]
            self.assertTrue(bridge_events, "At least one bridge.resolve_action event expected")
            for b in bridge_events:
                self.assertTrue(b["outputs"].get("selected_action_reason"), "bridge event must carry selected_action_reason")


if __name__ == "__main__":
    unittest.main()
