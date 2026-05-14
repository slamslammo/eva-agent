from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit import build_learning_outcome_record, evaluate_response_outcome
from scenarios.linux_runtime import activate_linux_runtime_scenario
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE


class LearningCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_peer_circuit_learning_reexports_encoding_helpers(self) -> None:
        observed_outcome, delta, label, confidence, outcome_vector = evaluate_response_outcome(
            {
                "execution_status": "completed",
                "pressure_outcome": "relieved",
                "followup_needed": False,
            },
            {
                "execution_status": "completed",
                "pressure_outcome": "relieved",
                "followup_needed": False,
                "uncertainty_after_action": "resolved_enough",
            },
        )

        self.assertEqual(observed_outcome, "relieved")
        self.assertEqual(delta, 1.0)
        self.assertEqual(label, "positive")
        self.assertGreaterEqual(confidence, 0.9)
        self.assertEqual(outcome_vector.to_dict()["viability_delta"], {"level_1": 1.0})
        self.assertTrue(callable(build_learning_outcome_record))


if __name__ == "__main__":
    unittest.main()
