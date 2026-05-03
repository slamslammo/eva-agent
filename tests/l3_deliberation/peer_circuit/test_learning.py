from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit import build_learning_outcome_record, evaluate_response_outcome


class LearningCompatibilityTests(unittest.TestCase):
    def test_peer_circuit_learning_reexports_encoding_helpers(self) -> None:
        observed_outcome, delta, label, confidence = evaluate_response_outcome(
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
        self.assertTrue(callable(build_learning_outcome_record))


if __name__ == "__main__":
    unittest.main()
