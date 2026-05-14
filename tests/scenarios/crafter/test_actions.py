from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass

from eva.kernel import ActivePressure, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import (
    ACTION_TO_ALLOWED_STATES,
    ALL_ACTIONS,
    DEFAULT_RESPONSE_MODE,
    NOOP_ACTION,
    SLEEP_ACTION,
    build_integrity_response_candidates,
    execute_crafter_action,
    filter_response_candidates,
)


@dataclass(frozen=True)
class StubStepResult:
    done: bool
    agent_observation: dict[str, object]
    before_observation: dict[str, object]
    after_action_observation: dict[str, object]


class StubRuntime:
    def __init__(self, step_result: StubStepResult) -> None:
        self.step_result = step_result
        self.actions: list[str] = []

    def step_external_action(self, action_name: str) -> StubStepResult:
        self.actions.append(action_name)
        return self.step_result


class CrafterActionTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_action_policy_exposes_expected_surface(self) -> None:
        self.assertEqual(DEFAULT_RESPONSE_MODE, "crafter_bounded_compatibility")
        self.assertEqual(len(ALL_ACTIONS), 17)
        self.assertIn(NOOP_ACTION, ACTION_TO_ALLOWED_STATES)
        self.assertIn(SLEEP_ACTION, ACTION_TO_ALLOWED_STATES)

    def test_integrity_candidates_are_bounded_and_filterable(self) -> None:
        pressure = ActivePressure(
            pressure_id="pressure-1",
            type="integrity",
            severity="degraded",
            evidence={"reason": "health_critical"},
            first_seen_at=utc_now(),
            last_seen_at=utc_now(),
            trend="worsening",
        )
        runtime_state = RuntimeState(life_state="STABLE", instance_valid=True)
        candidates = build_integrity_response_candidates(pressure, runtime_state)
        self.assertEqual([candidate.action for candidate in candidates], ["noop", "sleep", "do"])
        decisions = filter_response_candidates(pressure, runtime_state, candidates)
        self.assertTrue(all(decision.result == "allow" for decision in decisions))

    def test_execute_crafter_action_derives_real_deltas_from_runtime_step(self) -> None:
        before = {
            "visible": {
                "life_panel": {"values": {"health": 2, "food": 9, "water": 1, "energy": 4}},
                "inventory_panel": {"items": {"wood": 1, "stone": 0, "wood_pickaxe": 1}},
                "nearby_objects": ["zombie"],
                "local_view": {"nearby_objects": {"zombie": 1}},
            },
            "task_context": {"unlocked_achievements_visible": []},
        }
        after = {
            "visible": {
                "life_panel": {"values": {"health": 3, "food": 9, "water": 1, "energy": 4}},
                "inventory_panel": {"items": {"wood": 2, "stone": 0, "wood_pickaxe": 1}},
                "nearby_objects": [],
                "local_view": {"nearby_objects": {}},
            },
            "task_context": {"unlocked_achievements_visible": ["collect_wood"]},
        }
        runtime = StubRuntime(
            StubStepResult(
                done=False,
                agent_observation=after,
                before_observation=before,
                after_action_observation=after,
            )
        )
        pressure = ActivePressure(
            pressure_id="pressure-health",
            type="integrity",
            severity="critical",
            evidence={"reason": "health_critical"},
            first_seen_at=utc_now(),
            last_seen_at=utc_now(),
            trend="worsening",
        )
        selection = ResponseSelection(
            pressure_id=pressure.pressure_id,
            selected_action="do",
            selected_posture="crafter_candidate",
            selected_action_reason="test",
            filter_result="allow",
            candidate_actions=("do",),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            result = execute_crafter_action(store, pressure, selection, runtime=runtime)
        self.assertEqual(runtime.actions, ["do"])
        self.assertEqual(result["execution_status"], "completed")
        self.assertEqual(result["pressure_outcome"], "relieved")
        self.assertEqual(result["life_delta"], {"health": 1.0})
        self.assertEqual(result["inventory_delta"], {"wood": 1.0})
        self.assertEqual(result["achievement_delta"], 1.0)
        self.assertEqual(result["visible_threat_count"], 0)
        self.assertEqual(result["integration_hint"], "none")
        self.assertEqual(result["side_effects"], [])
        self.assertFalse(result["followup_needed"])

    def test_execute_crafter_action_marks_episode_reset_side_effect(self) -> None:
        before = {
            "visible": {
                "life_panel": {"values": {"health": 1, "food": 1, "water": 1, "energy": 1}},
                "inventory_panel": {"items": {}},
                "nearby_objects": ["zombie"],
                "local_view": {"nearby_objects": {"zombie": 1}},
            },
            "task_context": {"unlocked_achievements_visible": []},
        }
        after_action = {
            "visible": {
                "life_panel": {"values": {"health": 0, "food": 1, "water": 1, "energy": 1}},
                "inventory_panel": {"items": {}},
                "nearby_objects": ["zombie"] ,
                "local_view": {"nearby_objects": {"zombie": 1}},
            },
            "task_context": {"unlocked_achievements_visible": []},
        }
        runtime = StubRuntime(
            StubStepResult(
                done=True,
                agent_observation=before,
                before_observation=before,
                after_action_observation=after_action,
            )
        )
        pressure = ActivePressure(
            pressure_id="pressure-threat",
            type="integrity",
            severity="critical",
            evidence={"reason": "threat_visible"},
            first_seen_at=utc_now(),
            last_seen_at=utc_now(),
            trend="worsening",
        )
        selection = ResponseSelection(
            pressure_id=pressure.pressure_id,
            selected_action="sleep",
            selected_posture="crafter_candidate",
            selected_action_reason="test",
            filter_result="allow",
            candidate_actions=("sleep",),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            result = execute_crafter_action(store, pressure, selection, runtime=runtime)
        self.assertEqual(result["side_effects"], ["episode_reset"])
        self.assertEqual(result["pressure_outcome"], "unknown")
        self.assertTrue(result["followup_needed"])


if __name__ == "__main__":
    unittest.main()
