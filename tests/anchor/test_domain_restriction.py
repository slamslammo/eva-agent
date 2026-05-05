from __future__ import annotations

import unittest

from eva.l3_deliberation import build_action_domain, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_generation import ESCALATE_FIRST_PROFILE, OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE


class ActionDomainTests(unittest.TestCase):
    def test_action_domain_admits_both_candidate_schemas_by_default(self) -> None:
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

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(len(action_domain.admitted_candidate_schemas), 2)
        self.assertEqual(
            [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas],
            [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE],
        )
        self.assertEqual(action_domain.restriction_reasons, ("admitted_candidate_schemas=2",))
        self.assertEqual(action_domain.agent_state.seconds_to_heartbeat, 10.0)

    def test_action_domain_near_heartbeat_narrows_to_stabilize_first(self) -> None:
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
                "seconds_to_heartbeat": 0.4,
            },
        )

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(len(action_domain.admitted_candidate_schemas), 1)
        self.assertEqual(action_domain.admitted_candidate_schemas[0].candidate_profile, STABILIZE_FIRST_PROFILE)
        self.assertEqual(
            action_domain.restriction_reasons,
            ("admitted_candidate_schemas=1", "heartbeat_window_narrows_to_stabilize_first"),
        )

    def test_action_domain_preserves_habit_narrowing_inside_schema_admission(self) -> None:
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

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(len(action_domain.admitted_candidate_schemas), 1)
        schema = action_domain.admitted_candidate_schemas[0]
        self.assertEqual(schema.candidate_profile, STABILIZE_FIRST_PROFILE)
        self.assertTrue(schema.parameter_domain["habit_narrowed"])
        self.assertEqual(
            action_domain.restriction_reasons,
            ("admitted_candidate_schemas=1", "habit_candidate_narrowing"),
        )


    def test_action_domain_admits_escalate_first_for_high_risk_integrity_reason(self) -> None:
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
                "drive_levels": {"integrity": 0.9, "survival": 0.7},
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

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(len(action_domain.admitted_candidate_schemas), 3)
        self.assertEqual(
            [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas],
            [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE, ESCALATE_FIRST_PROFILE],
        )
        self.assertEqual(action_domain.agent_state.primary_pressure_reason, "runtime_files_missing")
        self.assertEqual(action_domain.agent_state.primary_pressure_severity, "critical")
        self.assertIn("high_risk_escalation_schema_admitted", action_domain.restriction_reasons)

    def test_action_domain_blocks_escalate_first_without_secondary_severity_gate(self) -> None:
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
                "drive_levels": {"integrity": 0.95, "survival": 0.8},
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

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(action_domain.agent_state.primary_pressure_reason, "runtime_files_missing")
        self.assertEqual(action_domain.agent_state.primary_pressure_severity, "degraded")
        self.assertEqual(
            [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas],
            [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE],
        )
        self.assertIn("high_risk_escalation_schema_blocked_by_secondary_gate", action_domain.restriction_reasons)
        self.assertNotIn("high_risk_escalation_schema_admitted", action_domain.restriction_reasons)

    def test_action_domain_does_not_admit_escalate_first_for_non_high_risk_reason(self) -> None:
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
                "drive_levels": {"integrity": 0.95, "survival": 0.8},
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
                        "pressure_id": "pressure-integrity-recent_yield_detected",
                        "type": "integrity",
                        "severity": "critical",
                        "evidence": {"reason": "recent_yield_detected"},
                    }
                ]
            },
        )

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(action_domain.agent_state.primary_pressure_reason, "recent_yield_detected")
        self.assertEqual(
            [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas],
            [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE],
        )
        self.assertNotIn(ESCALATE_FIRST_PROFILE, [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas])
        self.assertNotIn("high_risk_escalation_schema_admitted", action_domain.restriction_reasons)

    def test_action_domain_heartbeat_window_blocks_escalate_first_even_for_high_risk_reason(self) -> None:
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
                "drive_levels": {"integrity": 0.9, "survival": 0.7},
                "drive_trends": {"integrity": "worsening", "survival": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 0.5,
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

        action_domain = build_action_domain(deliberation_input)

        self.assertEqual(action_domain.agent_state.primary_pressure_reason, "runtime_files_missing")
        self.assertEqual(len(action_domain.admitted_candidate_schemas), 1)
        self.assertEqual(action_domain.admitted_candidate_schemas[0].candidate_profile, STABILIZE_FIRST_PROFILE)
        self.assertEqual(
            action_domain.restriction_reasons,
            ("admitted_candidate_schemas=1", "heartbeat_window_narrows_to_stabilize_first"),
        )

