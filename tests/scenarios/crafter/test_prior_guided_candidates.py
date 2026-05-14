from __future__ import annotations

import unittest

from eva.anchor.domain_restriction import build_action_domain
from eva.l3_deliberation import build_candidates, build_deliberation_input
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


if __name__ == "__main__":
    unittest.main()
