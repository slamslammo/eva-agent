from __future__ import annotations

import unittest

from eva.anchor.domain_restriction import build_action_domain
from eva.l3_deliberation import build_candidates, build_deliberation_input
from eva.l3_deliberation.peer_circuit.habit_track import shape_candidates_with_habit_track
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.prior_skills import prior_skill_registry


class CrafterPriorGuidedCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_survival_prior_aligns_with_stabilize_first_profile(self) -> None:
        registry = prior_skill_registry(
            top_drive="metabolic",
            life_state="STABLE",
            pressure_reason="water_critical",
        )
        records = registry.records()
        self.assertEqual(records[0].candidate_profile, "stabilize_first")

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
                "top_drive": "metabolic",
                "drive_levels": {
                    "metabolic": 0.9,
                    "safety": 0.1,
                    "recovery": 0.1,
                    "acquisition": 0.1,
                    "capability": 0.1,
                },
                "drive_trends": {
                    "metabolic": "worsening",
                    "safety": "unknown",
                    "recovery": "unknown",
                    "acquisition": "unknown",
                    "capability": "unknown",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
            pressure_table={
                "pressures": [
                    {
                        "type": "survival",
                        "severity": "critical",
                        "evidence": {"reason": "water_critical"},
                    }
                ]
            },
        )
        candidates = build_candidates(build_action_domain(deliberation_input))
        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], "stabilize_first")

    def test_inherited_prior_reorders_crafter_candidates_through_normal_shaping(self) -> None:
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
                "top_drive": "acquisition",
                "drive_levels": {
                    "metabolic": 0.2,
                    "safety": 0.1,
                    "recovery": 0.1,
                    "acquisition": 0.8,
                    "capability": 0.1,
                },
                "drive_trends": {
                    "metabolic": "unknown",
                    "safety": "unknown",
                    "recovery": "unknown",
                    "acquisition": "worsening",
                    "capability": "unknown",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
            pressure_table={
                "pressures": [
                    {
                        "type": "acquisition",
                        "severity": "critical",
                        "evidence": {"reason": "inventory_sparse"},
                    }
                ]
            },
            working_memory_context={
                "situation_key": "acquisition|STABLE|inventory_sparse",
                "bias_summaries": [],
                "habit_skills": [],
                "inherited_priors": [
                    {
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
                        "evidence_count": 3,
                        "stability_score": 0.7,
                        "confidence": 0.75,
                        "bias_strength": 0.6,
                    }
                ],
                "recent_relevant_outcomes": [],
                "semantic_patterns": [],
                "confidence": 0.75,
                "source_backend": "local_rule_based",
            },
        )

        shaped = shape_candidates_with_habit_track(
            build_candidates(build_action_domain(deliberation_input)),
            deliberation_input,
        )

        self.assertEqual(shaped[0].parameter_domain["candidate_profile"], "stabilize_first")
        self.assertEqual(shaped[0].parameter_domain["habit_hint_source"], "inherited_prior")

    def test_inherited_prior_bias_affects_crafter_assessment_through_normal_reasoning(self) -> None:
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
                "top_drive": "acquisition",
                "drive_levels": {
                    "metabolic": 0.2,
                    "safety": 0.1,
                    "recovery": 0.1,
                    "acquisition": 0.8,
                    "capability": 0.1,
                },
                "drive_trends": {
                    "metabolic": "unknown",
                    "safety": "unknown",
                    "recovery": "unknown",
                    "acquisition": "worsening",
                    "capability": "unknown",
                },
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
            pressure_table={
                "pressures": [
                    {
                        "type": "acquisition",
                        "severity": "critical",
                        "evidence": {"reason": "inventory_sparse"},
                    }
                ]
            },
            working_memory_context={
                "situation_key": "acquisition|STABLE|inventory_sparse",
                "bias_summaries": [],
                "habit_skills": [],
                "inherited_priors": [
                    {
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
                        "evidence_count": 3,
                        "stability_score": 0.7,
                        "confidence": 0.75,
                        "bias_strength": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
                "semantic_patterns": [],
                "confidence": 0.75,
                "source_backend": "local_rule_based",
            },
        )
        baseline_input = build_deliberation_input(
            signal_batch=deliberation_input.signal_batch,
            drive_broadcast=deliberation_input.drive_broadcast,
            runtime_gate_context=deliberation_input.runtime_gate_context,
            pressure_table=deliberation_input.compatibility_pressure_table,
            working_memory_context={
                "situation_key": "acquisition|STABLE|inventory_sparse",
                "bias_summaries": [],
                "habit_skills": [],
                "inherited_priors": [],
                "recent_relevant_outcomes": [],
                "semantic_patterns": [],
                "confidence": 0.75,
                "source_backend": "local_rule_based",
            },
        )

        assessments = assess_candidates(build_candidates(build_action_domain(deliberation_input)), deliberation_input)
        baseline_assessments = assess_candidates(
            build_candidates(build_action_domain(baseline_input)),
            baseline_input,
        )
        assessment_by_id = {assessment.candidate_id: assessment for assessment in assessments}
        baseline_by_id = {assessment.candidate_id: assessment for assessment in baseline_assessments}

        self.assertGreater(
            assessment_by_id["candidate-compatibility-stabilize-first"].learning_bias,
            baseline_by_id["candidate-compatibility-stabilize-first"].learning_bias,
        )
        self.assertIn(
            "inherited_prior_bias",
            assessment_by_id["candidate-compatibility-stabilize-first"].bias_reasons,
        )


if __name__ == "__main__":
    unittest.main()
