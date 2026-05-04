from __future__ import annotations

import unittest

from eva.l3_deliberation import build_action_domain, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_generation import OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE


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


if __name__ == "__main__":
    unittest.main()
