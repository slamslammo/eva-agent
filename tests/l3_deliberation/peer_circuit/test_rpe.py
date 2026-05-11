from __future__ import annotations

import unittest

from eva.l3_deliberation.peer_circuit.rpe import (
    build_learned_impact_overlay,
    build_learning_outcome_record,
    evaluate_response_outcome,
)
from eva.l3_deliberation import build_deliberation_input
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE


class RpeOwnerTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_runtime_scenario(LINUX_RUNTIME_SCENARIO_BUNDLE)

    def test_rpe_owner_evaluates_positive_relief_without_followup(self) -> None:
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

    def test_rpe_owner_builds_learning_outcome_record_with_stable_payload(self) -> None:
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
        audit_record = {
            "recorded_at": "2026-04-29T10:00:00+00:00",
            "deliberation_input": deliberation_input.to_dict(),
            "candidates": [],
            "assessments": [],
            "release_decision": {
                "outcome": "compatibility_release",
                "selected_action": "compatibility_release",
                "selected_candidate_id": "candidate-compatibility-stabilize-first",
                "rationale": ["compatibility_projection_present"],
                "release_context": {
                    "bridge_target": "pressure_led_compatibility",
                    "response_mode": "pressure_led_compatibility",
                    "candidate_profile": "stabilize_first",
                    "bridge_policy": {},
                },
                "expected_outcome": "stabilize_or_relieve_pressure",
            },
        }
        response_summary = {
            "pressure_id": "pressure-integrity-recent_yield_detected",
            "pressure_type": "integrity",
            "selected_action": "shrink_to_conservative_mode",
            "execution_status": "completed",
            "pressure_outcome": "relieved",
            "followup_needed": False,
            "response_mode": "pressure_led_compatibility",
            "drive_context": {"top_drive": "integrity"},
        }
        response_history_entry = {
            "response_id": "resp-001",
            "recorded_at": "2026-04-29T10:00:01+00:00",
            "response_mode": "pressure_led_compatibility",
            "pressure_id": "pressure-integrity-recent_yield_detected",
            "pressure_type": "integrity",
            "pressure_reason": "recent_yield_detected",
            "life_state": "STABLE",
            "selected_action": "shrink_to_conservative_mode",
            "execution_status": "completed",
            "pressure_outcome": "relieved",
            "followup_needed": False,
            "uncertainty_after_action": "resolved_enough",
            "drive_context": {"top_drive": "integrity"},
        }

        payload = build_learning_outcome_record(
            "2026-04-29T10:00:01+00:00",
            audit_record,
            response_summary,
            response_history_entry,
        ).to_dict()

        self.assertEqual(payload["expected_outcome"], "stabilize_or_relieve_pressure")
        self.assertEqual(payload["observed_outcome"], "relieved")
        self.assertEqual(payload["evaluation_label"], "positive")
        self.assertEqual(payload["candidate_profile"], "stabilize_first")
        self.assertEqual(payload["content"]["situation_key"], "integrity|STABLE|recent_yield_detected")
        self.assertTrue(payload["content"]["habit_skill_match"])
        self.assertFalse(payload["content"]["habit_narrowed"])
        self.assertEqual(payload["outcome_vector"]["viability_delta"], {"level_1": 1.0})
        self.assertEqual(payload["rpe_like_score"], payload["outcome_delta"])


    def test_rpe_owner_builds_learning_outcome_record_for_escalate_first(self) -> None:
        audit_record = {
            "recorded_at": "2026-05-05T10:00:00+00:00",
            "deliberation_input": {},
            "candidates": [],
            "assessments": [],
            "release_decision": {
                "outcome": "compatibility_release",
                "selected_action": "compatibility_release",
                "selected_candidate_id": "candidate-compatibility-escalate-first",
                "rationale": ["high_risk_projection_for_escalate_first"],
                "release_context": {
                    "bridge_target": "pressure_led_compatibility",
                    "response_mode": "pressure_led_compatibility",
                    "candidate_profile": "escalate_first",
                    "bridge_policy": {},
                },
                "expected_outcome": "escalate_for_safety_under_pressure",
            },
        }
        response_summary = {
            "pressure_id": "pressure-integrity-runtime_files_missing",
            "pressure_type": "integrity",
            "selected_action": "escalate_integrity_risk",
            "execution_status": "escalated",
            "pressure_outcome": "unchanged",
            "followup_needed": True,
            "response_mode": "pressure_led_compatibility",
            "drive_context": {"top_drive": "integrity"},
        }
        response_history_entry = {
            "response_id": "resp-escalate-001",
            "response_mode": "pressure_led_compatibility",
            "pressure_id": "pressure-integrity-runtime_files_missing",
            "pressure_type": "integrity",
            "pressure_reason": "runtime_files_missing",
            "life_state": "STABLE",
            "selected_action": "escalate_integrity_risk",
            "execution_status": "escalated",
            "pressure_outcome": "unchanged",
            "followup_needed": True,
            "uncertainty_after_action": "cannot_determine_safely",
            "drive_context": {"top_drive": "integrity"},
        }

        payload = build_learning_outcome_record(
            "2026-05-05T10:00:01+00:00",
            audit_record,
            response_summary,
            response_history_entry,
        ).to_dict()

        self.assertEqual(payload["expected_outcome"], "escalate_for_safety_under_pressure")
        self.assertEqual(payload["candidate_profile"], "escalate_first")
        self.assertTrue(payload["content"]["habit_skill_match"])
        self.assertEqual(payload["observed_outcome"], "escalated")

    def test_build_learned_impact_overlay_requires_thresholds(self) -> None:
        overlay, blend_factor = build_learned_impact_overlay(
            {
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 9,
                        "stability_score": 0.9,
                        "confidence": 0.9,
                        "last_outcome_delta": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
            },
            candidate_profile="observe_first",
            top_drive="curiosity",
        )

        self.assertEqual(overlay, {})
        self.assertEqual(blend_factor, 0.0)

    def test_build_learned_impact_overlay_returns_bounded_signal_after_threshold(self) -> None:
        overlay, blend_factor = build_learned_impact_overlay(
            {
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 12,
                        "stability_score": 0.9,
                        "confidence": 0.9,
                        "last_outcome_delta": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [],
            },
            candidate_profile="observe_first",
            top_drive="curiosity",
        )

        self.assertEqual(overlay, {"curiosity": 1.0})
        self.assertGreater(blend_factor, 0.0)
        self.assertLessEqual(blend_factor, 0.35)

    def test_build_learned_impact_overlay_blends_recent_relevant_outcome(self) -> None:
        overlay, blend_factor = build_learned_impact_overlay(
            {
                "bias_summaries": [
                    {
                        "candidate_profile": "observe_first",
                        "bias_strength": 1.0,
                        "evidence_count": 10,
                        "stability_score": 0.9,
                        "confidence": 0.9,
                        "last_outcome_delta": 1.0,
                    }
                ],
                "recent_relevant_outcomes": [
                    {
                        "candidate_profile": "observe_first",
                        "outcome_delta": -1.0,
                        "confidence": 0.9,
                    }
                ],
            },
            candidate_profile="observe_first",
            top_drive="curiosity",
        )

        self.assertEqual(overlay, {"curiosity": 0.5})
        self.assertEqual(blend_factor, 0.05)

