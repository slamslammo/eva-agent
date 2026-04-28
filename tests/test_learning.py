from __future__ import annotations

import unittest

from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation.learning import build_learning_outcome_record, evaluate_response_outcome
from eva.l3_deliberation.working_memory import build_working_memory_context, summarize_habit_bias


class LearningTests(unittest.TestCase):
    def test_evaluate_response_outcome_returns_positive_for_relieved_without_followup(self) -> None:
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

    def test_build_learning_outcome_record_uses_release_and_response_context(self) -> None:
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
                "rationale": ["integrity_or_threat_pressure_present"],
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

        record = build_learning_outcome_record(
            "2026-04-29T10:00:01+00:00",
            audit_record,
            response_summary,
            response_history_entry,
        )

        payload = record.to_dict()
        self.assertEqual(payload["expected_outcome"], "stabilize_or_relieve_pressure")
        self.assertEqual(payload["observed_outcome"], "relieved")
        self.assertEqual(payload["evaluation_label"], "positive")
        self.assertEqual(payload["candidate_profile"], "stabilize_first")
        self.assertEqual(payload["content"]["situation_key"], "integrity|STABLE|recent_yield_detected")

    def test_build_working_memory_context_returns_empty_safe_defaults(self) -> None:
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

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(context.situation_key, "curiosity|STABLE|none")
        self.assertEqual(context.bias_summaries, [])
        self.assertEqual(context.recent_relevant_outcomes, [])
        self.assertEqual(context.confidence, 0.0)

    def test_summarize_habit_bias_prefers_positive_profile(self) -> None:
        summaries = summarize_habit_bias(
            [
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "candidate_profile": "stabilize_first",
                    "selected_action": "shrink_to_conservative_mode",
                    "outcome_delta": -1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
            ],
            situation_key="integrity|STABLE|recent_yield_detected",
        )

        self.assertEqual(summaries[0].candidate_profile, "observe_first")
        self.assertGreater(summaries[0].bias_strength, 0.0)
        self.assertEqual(summaries[1].candidate_profile, "stabilize_first")
        self.assertLess(summaries[1].bias_strength, 0.0)


if __name__ == "__main__":
    unittest.main()
