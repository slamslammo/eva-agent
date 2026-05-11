from __future__ import annotations

import unittest

from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation.contracts import Candidate
from eva.l3_deliberation.peer_circuit.habit_track import (
    crystallized_habit_skill_hints,
    habitual_candidate_explanations,
    shape_candidates_with_habit_track,
)
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE


class HabitTrackOwnerTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_runtime_scenario(LINUX_RUNTIME_SCENARIO_BUNDLE)

    def test_habit_track_selects_strongest_crystallized_hint_per_profile(self) -> None:
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
            working_memory_context={
                "situation_key": "curiosity|STABLE|none",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "observe_first",
                        "preferred_action": "first",
                        "evidence_count": 3,
                        "stability_score": 0.7,
                        "confidence": 0.7,
                        "crystallized": True,
                    },
                    {
                        "candidate_profile": "observe_first",
                        "preferred_action": "second",
                        "evidence_count": 4,
                        "stability_score": 0.8,
                        "confidence": 0.9,
                        "crystallized": True,
                    },
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.9,
                "source_backend": "local_rule_based",
            },
        )

        hints = crystallized_habit_skill_hints(deliberation_input)

        self.assertEqual(hints["observe_first"]["preferred_action"], "second")
        self.assertEqual(hints["observe_first"]["evidence_count"], 4)
        self.assertEqual(hints["observe_first"]["stability_score"], 0.8)
        self.assertEqual(hints["observe_first"]["confidence"], 0.9)

    def test_habit_track_derives_habitual_explanations_from_recent_outcomes(self) -> None:
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
            working_memory_context={
                "situation_key": "curiosity|STABLE|none",
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "habit_eligible": False,
                        "habit_eligibility_reasons": ["recent_negative_streak"],
                    }
                ],
                "habit_skills": [],
                "recent_relevant_outcomes": [
                    {
                        "candidate_profile": "observe_first",
                        "outcome_delta": -1.0,
                        "evaluation_label": "negative",
                        "habit_narrowed": True,
                    }
                ],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        explanations = habitual_candidate_explanations(deliberation_input)

        self.assertEqual(explanations["observe_first"]["habitual_trace"], "habitual_suppression")
        self.assertIn("recent_negative_feedback", explanations["observe_first"]["habitual_trace_reasons"])
        self.assertIn("habit_narrowed", explanations["observe_first"]["habitual_trace_reasons"])
        self.assertFalse(explanations["observe_first"]["habit_eligible"])

    def test_habit_track_narrows_candidates_for_single_strong_skill(self) -> None:
        candidates = [
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "observe_first"},
                justification=("candidate_profile=observe_first",),
            ),
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "stabilize_first"},
                justification=("candidate_profile=stabilize_first",),
            ),
        ]
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
            working_memory_context={
                "situation_key": "curiosity|STABLE|none",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "shrink_to_conservative_mode",
                        "evidence_count": 4,
                        "stability_score": 0.8,
                        "confidence": 0.85,
                        "crystallized": True,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.85,
                "source_backend": "local_rule_based",
            },
        )

        shaped = shape_candidates_with_habit_track(candidates, deliberation_input)

        self.assertEqual(len(shaped), 1)
        self.assertEqual(shaped[0].parameter_domain["candidate_profile"], "stabilize_first")
        self.assertTrue(shaped[0].parameter_domain["habit_narrowed"])
        self.assertEqual(shaped[0].parameter_domain["habit_narrowed_from"], 2)
        self.assertIn("habit_candidate_narrowing", shaped[0].justification)

    def test_habit_track_does_not_narrow_when_multiple_strong_skills_exist(self) -> None:
        candidates = [
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "observe_first"},
                justification=("candidate_profile=observe_first",),
            ),
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "stabilize_first"},
                justification=("candidate_profile=stabilize_first",),
            ),
        ]
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
            working_memory_context={
                "situation_key": "curiosity|STABLE|none",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "observe_first",
                        "preferred_action": "recheck_runtime_integrity",
                        "evidence_count": 4,
                        "stability_score": 0.85,
                        "confidence": 0.9,
                        "crystallized": True,
                    },
                    {
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "shrink_to_conservative_mode",
                        "evidence_count": 4,
                        "stability_score": 0.8,
                        "confidence": 0.85,
                        "crystallized": True,
                    },
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.9,
                "source_backend": "local_rule_based",
            },
        )

        shaped = shape_candidates_with_habit_track(candidates, deliberation_input)

        self.assertEqual(len(shaped), 2)
        self.assertFalse(shaped[0].parameter_domain.get("habit_narrowed", False))

    def test_habit_track_reorders_candidates_without_removing_them(self) -> None:
        candidates = [
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "observe_first"},
                justification=("candidate_profile=observe_first",),
            ),
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={"candidate_profile": "stabilize_first"},
                justification=("candidate_profile=stabilize_first",),
            ),
        ]
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
            working_memory_context={
                "situation_key": "curiosity|STABLE|none",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "shrink_to_conservative_mode",
                        "evidence_count": 3,
                        "stability_score": 0.7,
                        "confidence": 0.75,
                        "crystallized": True,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.75,
                "source_backend": "local_rule_based",
            },
        )

        shaped = shape_candidates_with_habit_track(candidates, deliberation_input)

        self.assertEqual(len(shaped), 2)
        self.assertEqual(shaped[0].parameter_domain["candidate_profile"], "stabilize_first")
        self.assertTrue(shaped[0].parameter_domain["habit_skill_match"])
        self.assertEqual(shaped[0].parameter_domain["habit_preferred_action"], "shrink_to_conservative_mode")
        self.assertEqual(shaped[1].parameter_domain["candidate_profile"], "observe_first")


if __name__ == "__main__":
    unittest.main()
