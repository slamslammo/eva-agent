from __future__ import annotations

import unittest

from eva.l3_deliberation import Candidate, apply_structural_anchors, build_deliberation_input
from eva.l3_deliberation.candidates import OBSERVE_FIRST_PROFILE, build_candidates
from eva.l3_deliberation.value import assess_candidates


class ValueJudgmentTests(unittest.TestCase):
    def test_integrity_top_drive_allows_compatibility_release(self) -> None:
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

        assessments = assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input)

        self.assertEqual(len(assessments), 2)
        self.assertEqual(assessments[0].disposition, "allow")
        self.assertEqual(assessments[1].disposition, "allow")
        self.assertGreater(assessments[1].score, assessments[0].score)
        self.assertIn("candidate_profile=stabilize_first", assessments[1].reasons)

    def test_threat_signal_without_integrity_top_drive_still_allows_release(self) -> None:
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
                "top_drive": "survival",
                "drive_levels": {"survival": 0.8},
                "drive_trends": {"survival": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        assessments = assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input)

        self.assertEqual(assessments[0].disposition, "allow")
        self.assertEqual(assessments[1].disposition, "allow")
        self.assertIn("non_integrity_bias_for_observe_first", assessments[0].reasons)
        self.assertGreater(assessments[0].score, assessments[1].score)

    def test_conservative_mode_defers_release(self) -> None:
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
                "drive_levels": {"integrity": 0.5},
                "drive_trends": {"integrity": "stable"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": True,
                "life_state": "STABLE",
            },
        )

        assessments = assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input)

        self.assertEqual(assessments[0].disposition, "defer")
        self.assertIn("conservative_mode_active", assessments[0].reasons)

    def test_critical_state_defers_before_release(self) -> None:
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
                "life_state": "CRITICAL",
            },
        )

        assessments = assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input)

        self.assertEqual(assessments[0].disposition, "defer")
        self.assertIn("critical_life_state", assessments[0].reasons)

    def test_turn_block_withholds_before_release(self) -> None:
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
                "turn_allowed": False,
                "critical_blocked": True,
                "conservative_mode": False,
                "life_state": "CRITICAL",
            },
        )

        assessments = assess_candidates(apply_structural_anchors(build_candidates(deliberation_input), deliberation_input), deliberation_input)

        self.assertEqual(assessments[0].disposition, "withhold")
        self.assertIn("turn_not_allowed", assessments[0].reasons)

    def test_value_judgment_reads_runtime_boundaries_from_anchored_candidate_domain(self) -> None:
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
                "turn_allowed": False,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        candidate = Candidate(
            candidate_id="candidate-compatibility-observe-first",
            capability="compatibility_response",
            action="compatibility_release",
            parameter_domain={
                "top_drive": "integrity",
                "threat_signal_count": 1,
                "compatibility_pressure_count": 0,
                "candidate_profile": OBSERVE_FIRST_PROFILE,
                "turn_allowed": True,
            },
            justification=("candidate_profile=observe_first",),
        )

        anchored_candidate = apply_structural_anchors([candidate], deliberation_input)[0]
        assessment = assess_candidates([anchored_candidate], deliberation_input)[0]

        self.assertEqual(anchored_candidate.parameter_domain["turn_allowed"], False)
        self.assertEqual(assessment.disposition, "withhold")
        self.assertIn("turn_not_allowed", assessment.reasons)

    def test_unknown_candidate_action_is_withheld(self) -> None:
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
        candidates = [
            Candidate(
                candidate_id="candidate-unknown",
                capability="unknown_capability",
                action="unknown_action",
            )
        ]

        assessments = assess_candidates(candidates, deliberation_input)

        self.assertEqual(assessments[0].disposition, "withhold")
        self.assertIn("unknown_candidate_action", assessments[0].reasons)
        self.assertEqual(assessments[0].score, 0.0)


if __name__ == "__main__":
    unittest.main()
