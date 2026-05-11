from __future__ import annotations

import unittest

from eva.l3_deliberation import Candidate, apply_structural_anchors, build_action_domain, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_generation import build_candidates
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import ESCALATE_FIRST_PROFILE, LINUX_RUNTIME_SCENARIO_BUNDLE, OBSERVE_FIRST_PROFILE


class ValueJudgmentTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_runtime_scenario(LINUX_RUNTIME_SCENARIO_BUNDLE)

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
                "seconds_to_heartbeat": 10.0,
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

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
                "seconds_to_heartbeat": 10.0,
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(assessments[0].disposition, "allow")
        self.assertEqual(assessments[1].disposition, "allow")
        self.assertIn("non_integrity_projection_for_observe_first", assessments[0].reasons)
        self.assertGreater(assessments[1].score, assessments[0].score)

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

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

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

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

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
                "seconds_to_heartbeat": 10.0,
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

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

    def test_positive_habit_bias_only_adjusts_score_within_boundary(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 3,
                        "stability_score": 1.0,
                        "confidence": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertGreater(assessments[0].learning_bias, 0.0)
        self.assertEqual(assessments[0].disposition, "allow")
        self.assertIn("positive_habit_bias", assessments[0].bias_reasons)
        self.assertLessEqual(assessments[0].learning_bias, 0.35)

    def test_learning_bias_cannot_cross_turn_boundary(self) -> None:
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
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 3,
                        "stability_score": 1.0,
                        "confidence": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(assessments[0].disposition, "withhold")
        self.assertIn("turn_not_allowed", assessments[0].reasons)

    def test_recent_negative_outcome_adds_bounded_negative_bias(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "recent_relevant_outcomes": [
                    {
                        "candidate_profile": "observe_first",
                        "selected_action": "recheck_runtime_integrity",
                        "evaluation_label": "negative",
                        "outcome_delta": -1.0,
                        "confidence": 0.9,
                    }
                ],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertLess(assessments[0].learning_bias, 0.0)
        self.assertIn("recent_negative_outcome_bias", assessments[0].bias_reasons)
        self.assertIn("habitual_suppression_trace", assessments[0].reasons)
        self.assertEqual(assessments[0].disposition, "allow")
        self.assertGreaterEqual(assessments[0].learning_bias, -0.35)

    def test_recent_negative_outcome_only_affects_matching_profile(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "recent_relevant_outcomes": [
                    {
                        "candidate_profile": "observe_first",
                        "selected_action": "recheck_runtime_integrity",
                        "evaluation_label": "negative",
                        "outcome_delta": -1.0,
                        "confidence": 0.9,
                    }
                ],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertLess(assessments[0].learning_bias, 0.0)
        self.assertEqual(assessments[1].learning_bias, 0.0)
        self.assertNotIn("recent_negative_outcome_bias", assessments[1].bias_reasons)

    def test_low_confidence_recent_negative_outcome_does_not_apply_bias(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "recent_relevant_outcomes": [
                    {
                        "candidate_profile": "observe_first",
                        "selected_action": "recheck_runtime_integrity",
                        "evaluation_label": "negative",
                        "outcome_delta": -1.0,
                        "confidence": 0.4,
                    }
                ],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(assessments[0].learning_bias, 0.0)
        self.assertNotIn("recent_negative_outcome_bias", assessments[0].bias_reasons)

    def test_low_evidence_habit_summary_does_not_apply_bias(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 1,
                        "stability_score": 1.0,
                        "confidence": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(assessments[0].learning_bias, 0.0)
        self.assertNotIn("positive_habit_bias", assessments[0].bias_reasons)

    def test_crystallized_habit_skill_adds_small_priority_bonus(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "observe_first",
                        "preferred_action": "recheck_runtime_integrity",
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

        baseline_input = build_deliberation_input(
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "habit_skills": [],
                "recent_relevant_outcomes": [],
                "confidence": 0.0,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        baseline_assessments = assess_candidates(
            build_candidates(build_action_domain(baseline_input)),
            baseline_input,
        )

        self.assertGreater(assessments[0].score, baseline_assessments[0].score)
        self.assertIn("crystallized_habit_skill_hint", assessments[0].reasons)
        self.assertEqual(assessments[0].disposition, "allow")

    def test_non_crystallized_habit_skill_does_not_add_bonus(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "bias_summaries": [],
                "habit_skills": [
                    {
                        "candidate_profile": "observe_first",
                        "preferred_action": "recheck_runtime_integrity",
                        "evidence_count": 2,
                        "stability_score": 0.4,
                        "confidence": 0.45,
                        "crystallized": False,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.45,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertNotIn("crystallized_habit_skill_hint", assessments[0].reasons)

    def test_same_candidate_scores_differ_under_different_survival_levels(self) -> None:
        low_survival_input = build_deliberation_input(
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
                "drive_levels": {"survival": 0.1, "integrity": 0.2},
                "drive_trends": {"survival": "stable", "integrity": "stable"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )
        high_survival_input = build_deliberation_input(
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
                "drive_levels": {"survival": 0.9, "integrity": 0.2},
                "drive_trends": {"survival": "worsening", "integrity": "stable"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )

        low_assessment = assess_candidates(
            build_candidates(build_action_domain(low_survival_input)),
            low_survival_input,
        )[1]
        high_assessment = assess_candidates(
            build_candidates(build_action_domain(high_survival_input)),
            high_survival_input,
        )[1]

        self.assertEqual(low_assessment.disposition, "allow")
        self.assertEqual(high_assessment.disposition, "allow")
        self.assertGreater(high_assessment.score, low_assessment.score)

    def test_high_curiosity_prefers_observe_first_under_multi_drive_weighting(self) -> None:
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
                "top_drive": "curiosity",
                "drive_levels": {
                    "survival": 0.2,
                    "integrity": 0.1,
                    "continuity": 0.6,
                    "curiosity": 0.95,
                },
                "drive_trends": {
                    "survival": "stable",
                    "integrity": "stable",
                    "continuity": "stable",
                    "curiosity": "worsening",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(assessments[0].disposition, "allow")
        self.assertEqual(assessments[1].disposition, "allow")
        self.assertGreater(assessments[0].score, assessments[1].score)

    def test_zero_impact_schema_uses_projection_fallback_only(self) -> None:
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
                "drive_levels": {
                    "survival": 0.0,
                    "integrity": 0.8,
                    "continuity": 0.0,
                    "curiosity": 0.0,
                },
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )
        candidates = build_candidates(build_action_domain(deliberation_input))
        zeroed_candidates = [
            Candidate(
                candidate_id=candidate.candidate_id,
                capability=candidate.capability,
                action=candidate.action,
                parameter_domain=dict(candidate.parameter_domain),
                justification=tuple(candidate.justification),
                drive_impact_schema={},
                side_effect_class=candidate.side_effect_class,
            )
            for candidate in candidates
        ]

        assessments = assess_candidates(zeroed_candidates, deliberation_input)

        self.assertEqual(assessments[0].disposition, "allow")
        self.assertEqual(assessments[1].disposition, "allow")
        self.assertIn("projection_fallback", assessments[0].reasons)
        self.assertIn("projection_fallback", assessments[1].reasons)
        self.assertGreater(assessments[1].score, assessments[0].score)
        self.assertLess(assessments[1].score, 1.0)

    def test_unknown_candidate_action_withholds(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
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

    def test_llm_advisory_candidate_preference_adds_small_bounded_bonus(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "bias_summaries": [],
                "habit_skills": [],
                "recent_relevant_outcomes": [],
                "confidence": 0.61,
                "source_backend": "llm_assisted",
                "advisory_context": {
                    "candidate_suggestions": ["observe_first"],
                    "confidence": 0.61,
                },
            },
        )
        baseline_input = build_deliberation_input(
            signal_batch=deliberation_input.signal_batch,
            drive_broadcast=deliberation_input.drive_broadcast,
            runtime_gate_context=deliberation_input.runtime_gate_context,
            working_memory_context={
                "bias_summaries": [],
                "habit_skills": [],
                "recent_relevant_outcomes": [],
                "confidence": 0.61,
                "source_backend": "llm_assisted",
                "advisory_context": {},
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        baseline_assessments = assess_candidates(
            build_candidates(build_action_domain(baseline_input)),
            baseline_input,
        )

        self.assertGreater(assessments[0].score, baseline_assessments[0].score)
        self.assertIn("llm_advisory_candidate_preference", assessments[0].reasons)
        self.assertLessEqual(assessments[0].score - baseline_assessments[0].score, 0.12)
        self.assertEqual(assessments[0].disposition, "allow")

    def test_local_backend_ignores_llm_advisory_context(self) -> None:
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
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "bias_summaries": [],
                "habit_skills": [],
                "recent_relevant_outcomes": [],
                "confidence": 0.61,
                "source_backend": "local_rule_based",
                "advisory_context": {
                    "candidate_suggestions": ["observe_first"],
                    "confidence": 0.99,
                },
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertNotIn("llm_advisory_candidate_preference", assessments[0].reasons)

    def test_low_evidence_impact_learning_keeps_static_drive_impact_schema(self) -> None:
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
                "top_drive": "curiosity",
                "drive_levels": {
                    "survival": 0.2,
                    "integrity": 0.1,
                    "continuity": 0.6,
                    "curiosity": 0.95,
                },
                "drive_trends": {
                    "survival": "stable",
                    "integrity": "stable",
                    "continuity": "stable",
                    "curiosity": "worsening",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": -1.0,
                        "evidence_count": 9,
                        "stability_score": 0.95,
                        "confidence": 0.95,
                        "last_outcome_delta": -1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.95,
                "source_backend": "local_rule_based",
            },
        )
        baseline_input = build_deliberation_input(
            signal_batch=deliberation_input.signal_batch,
            drive_broadcast=deliberation_input.drive_broadcast,
            runtime_gate_context=deliberation_input.runtime_gate_context,
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        baseline_assessments = assess_candidates(
            build_candidates(build_action_domain(baseline_input)),
            baseline_input,
        )

        self.assertAlmostEqual(assessments[0].score, 0.36)
        self.assertNotIn("learned_impact_overlay", assessments[0].reasons)

    def test_thresholded_impact_learning_adds_bounded_overlay_to_drive_score(self) -> None:
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
                "top_drive": "curiosity",
                "drive_levels": {
                    "survival": 0.2,
                    "integrity": 0.1,
                    "continuity": 0.6,
                    "curiosity": 0.95,
                },
                "drive_trends": {
                    "survival": "stable",
                    "integrity": "stable",
                    "continuity": "stable",
                    "curiosity": "worsening",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": -1.0,
                        "evidence_count": 10,
                        "stability_score": 0.95,
                        "confidence": 0.95,
                        "last_outcome_delta": -1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.95,
                "source_backend": "local_rule_based",
            },
        )
        low_evidence_input = build_deliberation_input(
            signal_batch=deliberation_input.signal_batch,
            drive_broadcast=deliberation_input.drive_broadcast,
            runtime_gate_context=deliberation_input.runtime_gate_context,
            working_memory_context={
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": -1.0,
                        "evidence_count": 9,
                        "stability_score": 0.95,
                        "confidence": 0.95,
                        "last_outcome_delta": -1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 0.95,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        low_evidence_assessments = assess_candidates(
            build_candidates(build_action_domain(low_evidence_input)),
            low_evidence_input,
        )

        self.assertLess(assessments[0].score, low_evidence_assessments[0].score)
        self.assertIn("learned_impact_overlay", assessments[0].reasons)
        self.assertGreaterEqual(assessments[0].score, 0.0)

    def test_thresholded_impact_learning_remains_bounded_even_with_extreme_bias_inputs(self) -> None:
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
                "drive_levels": {
                    "survival": 0.0,
                    "integrity": 1.0,
                    "continuity": 0.0,
                    "curiosity": 0.0,
                },
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            working_memory_context={
                "bias_summaries": [
                    {
                        "candidate_profile": "stabilize_first",
                        "bias_strength": 99.0,
                        "evidence_count": 30,
                        "stability_score": 1.0,
                        "confidence": 1.0,
                        "last_outcome_delta": 99.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "confidence": 1.0,
                "source_backend": "local_rule_based",
            },
        )

        baseline_input = build_deliberation_input(
            signal_batch=deliberation_input.signal_batch,
            drive_broadcast=deliberation_input.drive_broadcast,
            runtime_gate_context=deliberation_input.runtime_gate_context,
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        baseline_assessments = assess_candidates(
            build_candidates(build_action_domain(baseline_input)),
            baseline_input,
        )

        self.assertLessEqual(assessments[1].score - baseline_assessments[1].score, 0.525)
        self.assertIn("learned_impact_overlay", assessments[1].reasons)

    def test_high_risk_integrity_reason_prefers_escalate_first(self) -> None:
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
                "drive_levels": {
                    "survival": 0.7,
                    "integrity": 0.95,
                    "continuity": 0.4,
                    "curiosity": 0.1,
                },
                "drive_trends": {"integrity": "worsening", "survival": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            pressure_table={
                "pressures": [
                    {
                        "pressure_id": "pressure-integrity-runtime_files_missing",
                        "type": "integrity",
                        "severity": "critical",
                        "evidence": {"reason": "runtime_files_missing"},
                    }
                ]
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(len(assessments), 3)
        self.assertEqual(assessments[2].candidate_id, "candidate-compatibility-escalate-first")
        self.assertEqual(assessments[2].disposition, "allow")
        self.assertIn("high_risk_projection_for_escalate_first", assessments[2].reasons)
        self.assertGreater(assessments[2].score, assessments[1].score)
        self.assertGreater(assessments[2].score, assessments[0].score)

    def test_high_risk_reason_without_secondary_severity_gate_does_not_materialize_escalate_first(self) -> None:
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
                "drive_levels": {
                    "survival": 0.7,
                    "integrity": 0.95,
                    "continuity": 0.4,
                    "curiosity": 0.1,
                },
                "drive_trends": {"integrity": "worsening", "survival": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            pressure_table={
                "pressures": [
                    {
                        "pressure_id": "pressure-integrity-runtime_files_missing",
                        "type": "integrity",
                        "severity": "degraded",
                        "evidence": {"reason": "runtime_files_missing"},
                    }
                ]
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)

        self.assertEqual(len(assessments), 2)
        self.assertNotIn(
            "candidate-compatibility-escalate-first",
            [assessment.candidate_id for assessment in assessments],
        )

