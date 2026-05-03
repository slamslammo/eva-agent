from __future__ import annotations

import unittest

from eva.l3_deliberation import CandidateAssessment, apply_structural_anchors, build_deliberation_input
from eva.l3_deliberation.peer_circuit.mediator import decide_release
from eva.l3_deliberation.reasoning.candidate_generation import build_candidates
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates


class MediatorTests(unittest.TestCase):
    def test_default_inhibition_withholds_without_release_pressure(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        decision = decide_release(assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input))

        self.assertEqual(decision.outcome, "withhold")
        self.assertIsNone(decision.selected_action)

    def test_integrity_pressure_releases_to_compatibility_path(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        decision = decide_release(assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input))

        self.assertEqual(decision.outcome, "compatibility_release")
        self.assertEqual(decision.selected_action, "compatibility_release")
        self.assertEqual(decision.selected_candidate_id, "candidate-compatibility-stabilize-first")
        self.assertEqual(
            decision.release_context,
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

    def test_blocked_runtime_defer_or_withhold(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": False,
                "critical_blocked": True,
                "conservative_mode": False,
                "life_state": "CRITICAL",
            },
        )

        decision = decide_release(assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input))

        self.assertIn(decision.outcome, {"withhold", "defer"})
        self.assertNotEqual(decision.outcome, "compatibility_release")
    def test_critical_without_turn_block_defers_release(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": True,
                "conservative_mode": False,
                "life_state": "CRITICAL",
            },
        )

        decision = decide_release(assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input))

        self.assertEqual(decision.outcome, "defer")
        self.assertEqual(decision.selected_action, "compatibility_release")

    def test_learning_bias_breaks_tie_within_allowed_candidates_only(self) -> None:
        assessments = [
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first",
                action="compatibility_release",
                score=1.25,
                disposition="allow",
                reasons=("candidate_profile=observe_first",),
                learning_bias=0.25,
                bias_reasons=("positive_habit_bias",),
            ),
            CandidateAssessment(
                candidate_id="candidate-compatibility-stabilize-first",
                action="compatibility_release",
                score=1.0,
                disposition="allow",
                reasons=("candidate_profile=stabilize_first",),
                learning_bias=0.0,
                bias_reasons=(),
            ),
        ]

        decision = decide_release(assessments)

        self.assertEqual(decision.outcome, "compatibility_release")
        self.assertEqual(decision.selected_candidate_id, "candidate-compatibility-observe-first")
        self.assertEqual(decision.learning_context["learning_bias"], 0.25)
        self.assertEqual(decision.learning_context["bias_reasons"], ["positive_habit_bias"])

    def test_learning_bias_cannot_override_higher_structural_score(self) -> None:
        assessments = [
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first",
                action="compatibility_release",
                score=1.3,
                disposition="allow",
                reasons=("candidate_profile=observe_first",),
                learning_bias=0.3,
                bias_reasons=("positive_habit_bias",),
            ),
            CandidateAssessment(
                candidate_id="candidate-compatibility-stabilize-first",
                action="compatibility_release",
                score=1.6,
                disposition="allow",
                reasons=("candidate_profile=stabilize_first",),
                learning_bias=0.0,
                bias_reasons=(),
            ),
        ]

        decision = decide_release(assessments)

        self.assertEqual(decision.outcome, "compatibility_release")
        self.assertEqual(decision.selected_candidate_id, "candidate-compatibility-stabilize-first")
        self.assertEqual(decision.learning_context["learning_bias"], 0.0)

    def test_habit_candidate_narrowing_sets_learning_context_trace(self) -> None:
        assessments = [
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first",
                action="compatibility_release",
                score=1.35,
                disposition="allow",
                reasons=("candidate_profile=observe_first", "habit_candidate_narrowing"),
                learning_bias=0.0,
                bias_reasons=(),
            )
        ]

        decision = decide_release(assessments)

        self.assertEqual(decision.outcome, "compatibility_release")
        self.assertEqual(decision.selected_candidate_id, "candidate-compatibility-observe-first")
        self.assertTrue(decision.learning_context["habit_narrowed"])
    def test_deferred_path_uses_first_deferred_assessment(self) -> None:
        assessments = [
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first",
                action="compatibility_release",
                score=0.0,
                disposition="withhold",
                reasons=("candidate_profile=observe_first", "no_release_pressure"),
                learning_bias=0.0,
                bias_reasons=(),
            ),
            CandidateAssessment(
                candidate_id="candidate-compatibility-stabilize-first",
                action="compatibility_release",
                score=0.0,
                disposition="defer",
                reasons=("candidate_profile=stabilize_first", "critical_runtime_boundary"),
                learning_bias=0.0,
                bias_reasons=(),
            ),
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first-alt",
                action="compatibility_release",
                score=0.0,
                disposition="defer",
                reasons=("candidate_profile=observe_first", "conservative_mode_active"),
                learning_bias=0.0,
                bias_reasons=(),
            ),
        ]

        decision = decide_release(assessments)

        self.assertEqual(decision.outcome, "defer")
        self.assertEqual(decision.selected_candidate_id, "candidate-compatibility-stabilize-first")
        self.assertEqual(decision.rationale, ("candidate_profile=stabilize_first", "critical_runtime_boundary"))

    def test_withhold_path_uses_first_assessment_for_trace_context(self) -> None:
        assessments = [
            CandidateAssessment(
                candidate_id="candidate-compatibility-observe-first",
                action="compatibility_release",
                score=0.0,
                disposition="withhold",
                reasons=("candidate_profile=observe_first", "no_release_pressure"),
                learning_bias=-0.1,
                bias_reasons=("negative_habit_bias",),
            ),
            CandidateAssessment(
                candidate_id="candidate-compatibility-stabilize-first",
                action="compatibility_release",
                score=0.0,
                disposition="withhold",
                reasons=("candidate_profile=stabilize_first", "no_release_pressure"),
                learning_bias=0.2,
                bias_reasons=("positive_habit_bias",),
            ),
        ]

        decision = decide_release(assessments)

        self.assertEqual(decision.outcome, "withhold")
        self.assertIsNone(decision.selected_candidate_id)
        self.assertEqual(decision.rationale, ("candidate_profile=observe_first", "no_release_pressure"))
        self.assertEqual(
            decision.learning_context,
            {
                "candidate_profile": "observe_first",
                "learning_bias": -0.1,
                "bias_reasons": ["negative_habit_bias"],
                "habit_narrowed": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
