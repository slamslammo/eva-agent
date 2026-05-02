from __future__ import annotations
import tempfile
import unittest
from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input, build_learning_outcome_record, evaluate_response_outcome
from eva.l3_deliberation.memory import derive_habit_skills
from eva.l3_deliberation.reasoning import build_working_memory_context, build_working_memory_context_from_store, summarize_habit_bias
from eva.l3_deliberation.memory import (
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
)
from eva.l3_deliberation.memory import (
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_HEURISTIC,
    NullWorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    WorkingMemoryModelClientResponse,
    build_builtin_working_memory_model_client,
)


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
        self.assertTrue(payload["content"]["habit_skill_match"])
        self.assertFalse(payload["content"]["habit_narrowed"])

    def test_build_learning_outcome_record_carries_habit_narrowing_trace(self) -> None:
        audit_record = {
            "recorded_at": "2026-04-29T10:00:00+00:00",
            "deliberation_input": {},
            "candidates": [],
            "assessments": [],
            "release_decision": {
                "outcome": "compatibility_release",
                "selected_action": "compatibility_release",
                "selected_candidate_id": "candidate-compatibility-stabilize-first",
                "rationale": ["habit_candidate_narrowing"],
                "release_context": {
                    "bridge_target": "pressure_led_compatibility",
                    "response_mode": "pressure_led_compatibility",
                    "candidate_profile": "stabilize_first",
                    "bridge_policy": {},
                },
                "expected_outcome": "stabilize_or_relieve_pressure",
                "learning_context": {
                    "candidate_profile": "stabilize_first",
                    "learning_bias": 0.0,
                    "bias_reasons": [],
                    "habit_narrowed": True,
                },
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

        self.assertTrue(record.to_dict()["content"]["habit_skill_match"])
        self.assertTrue(record.to_dict()["content"]["habit_narrowed"])


if __name__ == "__main__":
    unittest.main()
