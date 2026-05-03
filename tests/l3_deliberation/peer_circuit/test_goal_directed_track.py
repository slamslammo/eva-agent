from __future__ import annotations

import unittest

from eva.l3_deliberation import CandidateAssessment
from eva.l3_deliberation.peer_circuit.goal_directed_track import (
    build_learning_context,
    build_release_context,
    candidate_profile_from_id,
    expected_outcome_for_release,
)


class GoalDirectedTrackOwnerTests(unittest.TestCase):
    def test_goal_directed_track_maps_candidate_profile_from_id(self) -> None:
        self.assertEqual(candidate_profile_from_id("candidate-compatibility-observe-first"), "observe_first")
        self.assertEqual(candidate_profile_from_id("candidate-compatibility-stabilize-first"), "stabilize_first")
        self.assertEqual(candidate_profile_from_id("candidate-compatibility-other"), "unknown")
        self.assertEqual(candidate_profile_from_id(None), "unknown")

    def test_goal_directed_track_builds_release_context_for_stabilize_first(self) -> None:
        self.assertEqual(
            build_release_context("stabilize_first"),
            {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "stabilize_first",
                "bridge_policy": {
                    "policy_name": "stabilize_first_bias",
                    "selection": {
                        "preferred_action": "shrink_to_conservative_mode",
                        "fallback_action": "recheck_runtime_integrity",
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": True,
                    },
                },
            },
        )

    def test_goal_directed_track_builds_learning_context_from_selected_assessment(self) -> None:
        assessment = CandidateAssessment(
            candidate_id="candidate-compatibility-observe-first",
            action="compatibility_release",
            score=1.2,
            disposition="allow",
            reasons=("candidate_profile=observe_first", "habit_candidate_narrowing"),
            learning_bias=0.25,
            bias_reasons=("positive_habit_bias",),
        )

        self.assertEqual(
            build_learning_context(assessment),
            {
                "candidate_profile": "observe_first",
                "learning_bias": 0.25,
                "bias_reasons": ["positive_habit_bias"],
                "habit_narrowed": True,
            },
        )

    def test_goal_directed_track_preserves_expected_outcome_labels(self) -> None:
        self.assertEqual(
            expected_outcome_for_release("compatibility_release", "observe_first"),
            "improve_information_under_pressure",
        )
        self.assertEqual(
            expected_outcome_for_release("compatibility_release", "stabilize_first"),
            "stabilize_or_relieve_pressure",
        )
        self.assertEqual(
            expected_outcome_for_release("compatibility_release", "unknown"),
            "bounded_pressure_response",
        )
        self.assertEqual(expected_outcome_for_release("defer", "observe_first"), "wait_for_safer_boundary")
        self.assertEqual(expected_outcome_for_release("withhold", "observe_first"), "no_external_change")


if __name__ == "__main__":
    unittest.main()
