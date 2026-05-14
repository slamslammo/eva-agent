from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import ExternalLifeConfig, LifecycleConfig, LoopControl, StateStore, build_runtime_config
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario


class StubCrafterSession:
    def __init__(self) -> None:
        self.wrapper = None
        self.closed = False
        self.step_actions: list[str] = []
        self.latest_agent_observation = self._observation(health=2, wood=1, threat_count=1, achievements=[])

    @classmethod
    def start(cls, *, seed: int | None = None) -> "StubCrafterSession":
        del seed
        return cls()

    def _observation(self, *, health: int, wood: int, threat_count: int, achievements: list[str]) -> dict[str, object]:
        nearby = {"zombie": threat_count} if threat_count else {}
        return {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "episode-1",
            "step": 0,
            "visible": {
                "local_view": {
                    "nearby_objects": nearby,
                    "nearby_materials": {"tree": 1},
                },
                "life_panel": {"available": True, "values": {"health": health, "food": 9, "water": 9, "energy": 9}},
                "inventory_panel": {"available": True, "items": {"wood": wood}},
                "nearby_objects": ["zombie"] if threat_count else [],
            },
            "task_context": {
                "objective": "survive and unlock achievements",
                "unlocked_achievements_visible": achievements,
            },
            "available_actions": ["noop", "sleep", "do"],
            "notes": [],
        }

    def build_shared_facts(self) -> dict[str, object]:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str):
        self.step_actions.append(action_name)
        before = dict(self.latest_agent_observation)
        after = self._observation(health=3, wood=2, threat_count=0, achievements=["collect_wood"])
        self.latest_agent_observation = after
        return type(
            "CrafterActionStep",
            (),
            {
                "raw_observation": None,
                "reward": 1.0,
                "done": False,
                "raw_info": {},
                "agent_observation": after,
                "before_observation": before,
                "after_action_observation": after,
            },
        )()

    def close(self) -> None:
        self.closed = True


class CrafterRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_bounded_run_executes_crafter_patrol_and_response_with_shared_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                summary = run_crafter_runtime(config)
            self.assertGreaterEqual(summary.turns, 1)
            self.assertGreaterEqual(len(stub_session.step_actions), 1)
            store = StateStore(config.paths)
            snapshot = store.read_external_life_snapshot()
            assert snapshot is not None
            self.assertIn(snapshot.primary_gap["type"], {"avatar_safety", "avatar_metabolic", "avatar_recovery", "inventory_capability", "inventory_acquisition", "local_view_state"})
            self.assertGreaterEqual(len(store.read_response_history()), 1)
            response = store.read_response_history()[-1]
            self.assertIn("life_delta", response)
            self.assertIn("inventory_delta", response)
            self.assertIn("achievement_delta", response)
            self.assertIn("visible_threat_count", response)
            self.assertGreaterEqual(len(store.read_learning_outcomes()), 1)
            self.assertTrue(config.paths.events_file.exists())
            self.assertTrue(config.paths.learning_outcomes_file.exists())
            self.assertTrue(stub_session.closed)

    def test_bounded_run_releases_action_even_when_first_crafter_pressure_is_non_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config)
            store = StateStore(config.paths)
            response_history = store.read_response_history()
            self.assertGreaterEqual(len(stub_session.step_actions), 1)
            self.assertGreaterEqual(len(response_history), 1)
            self.assertIn(response_history[-1]["pressure_type"], {"safety", "metabolic", "recovery", "acquisition", "capability"})


if __name__ == "__main__":
    unittest.main()
