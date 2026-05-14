from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit.rpe import build_learning_outcome_record
from scenarios.crafter import activate_crafter_scenario


class CrafterLearningIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_learning_record_preserves_multidimensional_outcome_fields(self) -> None:
        record = build_learning_outcome_record(
            "2026-05-13T00:00:00Z",
            {
                "recorded_at": "2026-05-13T00:00:00Z",
                "release_decision": {
                    "outcome": "compatibility_release",
                    "selected_action": "do",
                    "release_context": {
                        "candidate_profile": "escalate_first",
                        "response_mode": "crafter_bounded_compatibility",
                    },
                    "learning_context": {},
                },
            },
            {
                "selected_action": "do",
                "achievement_delta": 1.0,
                "inventory_delta": {"wood": 1.0},
                "life_delta": {"health": -1.0, "energy": -0.5},
                "visible_threat_count": 1,
                "followup_needed": False,
            },
            {
                "response_id": "response-1",
                "selected_action": "do",
                "pressure_reason": "threat_visible",
                "response_mode": "crafter_bounded_compatibility",
                "life_state": "STABLE",
                "drive_context": {"top_drive": "safety"},
            },
        )
        payload = record.to_dict()
        vector = payload["outcome_vector"]
        self.assertEqual(vector["task_progress"], 1.0)
        self.assertEqual(vector["resource_delta"], {"wood": 1.0})
        self.assertEqual(vector["viability_delta"], {"health": -1.0, "energy": -0.5})
        self.assertIsNotNone(vector["risk_delta"])
        self.assertIn("cost", vector)


if __name__ == "__main__":
    unittest.main()
