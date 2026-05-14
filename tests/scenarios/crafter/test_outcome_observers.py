from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit.rpe import build_learning_outcome_record, evaluate_response_outcome
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.outcome_observers.compatibility import OUTCOME_DELTA_WEIGHTS


class CrafterOutcomeObserverTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_sleep_observer_produces_viability_vector(self) -> None:
        observed, delta, label, confidence, outcome_vector = evaluate_response_outcome(
            {
                "selected_action": "sleep",
                "life_delta": {"energy": 1.0},
                "pressure_outcome": "unknown",
                "followup_needed": False,
            }
        )
        self.assertEqual(observed, "improved")
        self.assertGreater(delta, 0.0)
        self.assertEqual(label, "positive")
        self.assertGreater(confidence, 0.0)
        self.assertEqual(outcome_vector.viability_delta, {"energy": 1.0})
        self.assertEqual(outcome_vector.cost, {"action_count": 1.0})

    def test_learning_record_carries_outcome_vector(self) -> None:
        record = build_learning_outcome_record(
            "2026-05-13T00:00:00Z",
            {
                "recorded_at": "2026-05-13T00:00:00Z",
                "release_decision": {
                    "outcome": "compatibility_release",
                    "selected_action": "sleep",
                    "release_context": {"candidate_profile": "stabilize_first", "response_mode": "crafter_bounded_compatibility"},
                    "learning_context": {},
                },
            },
            {
                "selected_action": "sleep",
                "life_delta": {"energy": 1.0},
                "pressure_outcome": "unknown",
                "followup_needed": False,
            },
            {
                "response_id": "response-1",
                "selected_action": "sleep",
                "pressure_reason": "energy_critical",
                "response_mode": "crafter_bounded_compatibility",
                "life_state": "STABLE",
                "drive_context": {"top_drive": "recovery"},
            },
        )
        payload = record.to_dict()
        self.assertEqual(payload["observed_outcome"], "improved")
        self.assertEqual(payload["evaluation_label"], "positive")
        self.assertIn("outcome_vector", payload)
        self.assertEqual(payload["outcome_vector"]["viability_delta"], {"energy": 1.0})

    def test_task_progress_requires_achievement_delta(self) -> None:
        observed, delta, label, confidence, outcome_vector = evaluate_response_outcome(
            {
                "selected_action": "make_wood_pickaxe",
                "achievement_delta": 0.0,
                "inventory_delta": {"wood": -1.0},
                "life_delta": {},
                "followup_needed": False,
            }
        )
        self.assertEqual(observed, "improved")
        self.assertGreater(delta, 0.0)
        self.assertEqual(label, "positive")
        self.assertGreater(confidence, 0.0)
        self.assertIsNone(outcome_vector.task_progress)
        self.assertEqual(outcome_vector.capability_delta, {"craft_or_place": 1.0})

    def test_outcome_delta_uses_named_weights(self) -> None:
        observed, delta, label, confidence, outcome_vector = evaluate_response_outcome(
            {
                "selected_action": "make_wood_pickaxe",
                "achievement_delta": 1.0,
                "inventory_delta": {"wood": 2.0},
                "life_delta": {"energy": 1.0},
                "followup_needed": False,
            }
        )
        expected = round(
            (OUTCOME_DELTA_WEIGHTS["viability"] * 1.0)
            + (OUTCOME_DELTA_WEIGHTS["resource"] * 2.0)
            + (OUTCOME_DELTA_WEIGHTS["capability"] * 1.0),
            3,
        )
        self.assertEqual(observed, "improved")
        self.assertEqual(delta, expected)
        self.assertEqual(label, "positive")
        self.assertGreater(confidence, 0.0)
        self.assertEqual(outcome_vector.task_progress, 1.0)

    def test_make_without_achievement_keeps_task_progress_empty_in_learning_record(self) -> None:
        record = build_learning_outcome_record(
            "2026-05-13T00:00:00Z",
            {
                "recorded_at": "2026-05-13T00:00:00Z",
                "release_decision": {
                    "outcome": "compatibility_release",
                    "selected_action": "make_wood_pickaxe",
                    "release_context": {"candidate_profile": "observe_first", "response_mode": "crafter_bounded_compatibility"},
                    "learning_context": {},
                },
            },
            {
                "selected_action": "make_wood_pickaxe",
                "achievement_delta": 0.0,
                "inventory_delta": {"wood": -1.0},
                "followup_needed": False,
            },
            {
                "response_id": "response-2",
                "selected_action": "make_wood_pickaxe",
                "pressure_reason": "tools_missing_for_progress",
                "response_mode": "crafter_bounded_compatibility",
                "life_state": "STABLE",
                "drive_context": {"top_drive": "capability"},
            },
        )
        payload = record.to_dict()
        self.assertIsNone(payload["outcome_vector"]["task_progress"])
        self.assertEqual(payload["outcome_vector"]["capability_delta"], {"craft_or_place": 1.0})


if __name__ == "__main__":
    unittest.main()
