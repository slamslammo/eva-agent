from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit.rpe import build_learning_outcome_record, evaluate_response_outcome
from scenarios.crafter import activate_crafter_scenario


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


if __name__ == "__main__":
    unittest.main()
