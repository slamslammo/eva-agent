from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, ActivePressureTable, utc_now
from eva.l3_deliberation import apply_structural_anchors, build_deliberation_input
from eva.l3_deliberation.candidates import OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE, build_candidates
from eva.l3_deliberation.contracts import Candidate, DeliberationInput


class CandidateGenerationTests(unittest.TestCase):
    def test_build_candidates_uses_b0_input_contract(self) -> None:
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

        candidates = build_candidates(deliberation_input)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].action, "compatibility_release")
        self.assertEqual(candidates[0].parameter_domain["top_drive"], "curiosity")
        self.assertEqual(candidates[0].parameter_domain["threat_signal_count"], 0)
        self.assertEqual(candidates[0].parameter_domain["compatibility_pressure_count"], 0)
        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], OBSERVE_FIRST_PROFILE)
        self.assertEqual(candidates[1].parameter_domain["candidate_profile"], STABILIZE_FIRST_PROFILE)
        self.assertNotIn("instance_valid", candidates[0].parameter_domain)
        self.assertNotIn("turn_allowed", candidates[0].parameter_domain)
        self.assertNotIn("critical_blocked", candidates[0].parameter_domain)
        self.assertNotIn("conservative_mode", candidates[0].parameter_domain)
        self.assertNotIn("life_state", candidates[0].parameter_domain)
        self.assertEqual(
            candidates[0].justification,
            ("candidate_profile=observe_first", "top_drive=curiosity", "threat_signal_count=0"),
        )

    def test_deliberation_input_rejects_missing_b0_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "signal_batch missing required keys"):
            DeliberationInput(
                signal_batch={"signals": []},
                drive_broadcast={"top_drive": "curiosity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
            )

    def test_deliberation_input_rejects_missing_drive_broadcast_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "drive_broadcast missing required keys"):
            DeliberationInput(
                signal_batch={"signals": [], "summary": {}},
                drive_broadcast={"top_drive": "curiosity", "drive_levels": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
            )

    def test_deliberation_input_rejects_missing_runtime_gate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "runtime_gate_context missing required keys"):
            DeliberationInput(
                signal_batch={"signals": [], "summary": {}},
                drive_broadcast={"top_drive": "curiosity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                },
            )

    def test_compatibility_pressure_table_stays_explicitly_noncanonical(self) -> None:
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
            pressure_table={"pressures": [{"pressure_id": "p1"}]},
        )

        self.assertNotIn("compatibility_pressure_table", {"signal_batch", "drive_broadcast", "runtime_gate_context"})
        self.assertEqual(deliberation_input.compatibility_pressure_table["pressures"][0]["pressure_id"], "p1")
        self.assertEqual(build_candidates(deliberation_input)[0].parameter_domain["compatibility_pressure_count"], 1)
        self.assertEqual(build_candidates(deliberation_input)[1].parameter_domain["compatibility_pressure_count"], 1)

    def test_build_deliberation_input_accepts_active_pressure_table(self) -> None:
        now = utc_now()
        pressure_table = ActivePressureTable(
            captured_at=now,
            pressures=[
                ActivePressure(
                    pressure_id="pressure-integrity-instance_invalid",
                    type="integrity",
                    severity="critical",
                    evidence={"reason": "instance_invalid"},
                    first_seen_at=now,
                    last_seen_at=now,
                    trend="worsening",
                    active=True,
                )
            ],
            updated_at=now,
        )
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
            pressure_table=pressure_table,
        )

        self.assertEqual(
            deliberation_input.to_dict()["compatibility_pressure_table"]["pressures"][0]["pressure_id"],
            "pressure-integrity-instance_invalid",
        )
        self.assertEqual(build_candidates(deliberation_input)[0].parameter_domain["compatibility_pressure_count"], 1)
        self.assertEqual(build_candidates(deliberation_input)[1].parameter_domain["compatibility_pressure_count"], 1)

    def test_build_deliberation_input_accepts_working_memory_context(self) -> None:
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
                "habit_skills": [],
                "recent_relevant_outcomes": [],
                "confidence": 0.0,
                "source_backend": "local_rule_based",
            },
        )

        self.assertEqual(deliberation_input.working_memory_context["situation_key"], "curiosity|STABLE|none")
        self.assertEqual(deliberation_input.working_memory_context["habit_skills"], [])
        self.assertIn("working_memory_context", deliberation_input.to_dict())

    def test_single_strong_crystallized_habit_skill_can_narrow_candidates(self) -> None:
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

        candidates = build_candidates(deliberation_input)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], STABILIZE_FIRST_PROFILE)
        self.assertTrue(candidates[0].parameter_domain["habit_narrowed"])
        self.assertEqual(candidates[0].parameter_domain["habit_narrowed_from"], 2)
        self.assertEqual(candidates[0].parameter_domain["habitual_trace"], "habitual_neutral")
        self.assertTrue(candidates[0].parameter_domain["habit_eligible"])
        self.assertIn("habit_candidate_narrowing", candidates[0].justification)

    def test_candidate_building_surfaces_habitual_suppression_explanation(self) -> None:
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
                        "habitual_trace": "habitual_suppression",
                        "habitual_trace_reasons": ["recent_negative_feedback"],
                    }
                ],
                "confidence": 0.5,
                "source_backend": "local_rule_based",
            },
        )

        candidates = build_candidates(deliberation_input)

        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], OBSERVE_FIRST_PROFILE)
        self.assertEqual(candidates[0].parameter_domain["habitual_trace"], "habitual_suppression")
        self.assertIn("recent_negative_feedback", candidates[0].parameter_domain["habitual_trace_reasons"])
        self.assertFalse(candidates[0].parameter_domain["habit_eligible"])
        self.assertIn("habitual_suppression_trace", candidates[0].justification)

    def test_multiple_crystallized_habit_skills_do_not_narrow_candidates(self) -> None:
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

        candidates = build_candidates(deliberation_input)

        self.assertEqual(len(candidates), 2)
        self.assertFalse(candidates[0].parameter_domain.get("habit_narrowed", False))

    def test_crystallized_habit_skill_reorders_candidate_priority_without_removing_candidates(self) -> None:
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

        candidates = build_candidates(deliberation_input)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], STABILIZE_FIRST_PROFILE)
        self.assertTrue(candidates[0].parameter_domain["habit_skill_match"])
        self.assertEqual(candidates[0].parameter_domain["habit_preferred_action"], "shrink_to_conservative_mode")
        self.assertEqual(candidates[1].parameter_domain["candidate_profile"], OBSERVE_FIRST_PROFILE)

    def test_structural_anchors_only_restrict_parameter_domain(self) -> None:
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
                "turn_allowed": False,
                "critical_blocked": True,
                "conservative_mode": True,
                "life_state": "CRITICAL",
            },
        )
        candidate = Candidate(
            candidate_id="candidate-1",
            capability="compatibility_response",
            action="compatibility_release",
            parameter_domain={"top_drive": "curiosity", "threat_signal_count": 0},
            justification=("top_drive=curiosity",),
        )

        anchored = apply_structural_anchors([candidate], deliberation_input)

        self.assertEqual(len(anchored), 1)
        self.assertEqual(anchored[0].candidate_id, "candidate-1")
        self.assertEqual(anchored[0].capability, "compatibility_response")
        self.assertEqual(anchored[0].action, "compatibility_release")
        self.assertEqual(anchored[0].justification, ("top_drive=curiosity",))
        self.assertEqual(candidate.parameter_domain, {"top_drive": "curiosity", "threat_signal_count": 0})
        self.assertEqual(anchored[0].parameter_domain["top_drive"], "curiosity")
        self.assertEqual(anchored[0].parameter_domain["threat_signal_count"], 0)
        self.assertEqual(anchored[0].parameter_domain["instance_valid"], True)
        self.assertEqual(anchored[0].parameter_domain["turn_allowed"], False)
        self.assertEqual(anchored[0].parameter_domain["critical_blocked"], True)
        self.assertEqual(anchored[0].parameter_domain["conservative_mode"], True)
        self.assertEqual(anchored[0].parameter_domain["life_state"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
