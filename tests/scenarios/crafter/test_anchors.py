from __future__ import annotations

import unittest

from eva.anchor.domain_restriction import build_action_domain
from eva.l3_deliberation import build_deliberation_input, build_candidates
from scenarios.crafter import activate_crafter_scenario


class CrafterAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def _base_input(self, *, top_drive: str, drive_levels: dict[str, float], pressure_reason: str = "none"):
        return build_deliberation_input(
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
                "top_drive": top_drive,
                "drive_levels": drive_levels,
                "drive_trends": {name: "unknown" for name in drive_levels},
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
                        "type": "safety",
                        "severity": "critical",
                        "evidence": {"reason": pressure_reason},
                    }
                ]
            },
        )

    def test_high_safety_admits_escalate_first(self) -> None:
        deliberation_input = self._base_input(
            top_drive="safety",
            drive_levels={
                "metabolic": 0.1,
                "safety": 0.9,
                "recovery": 0.2,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="health_critical",
        )
        action_domain = build_action_domain(deliberation_input)
        profiles = [schema.candidate_profile for schema in action_domain.admitted_candidate_schemas]
        self.assertIn("escalate_first", profiles)
        self.assertIn("low_health_no_engagement", action_domain.restriction_reasons)

    def test_high_metabolic_prefers_stabilize_first(self) -> None:
        deliberation_input = self._base_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.8,
                "safety": 0.2,
                "recovery": 0.2,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="water_critical",
        )
        candidates = build_candidates(build_action_domain(deliberation_input))
        self.assertEqual(candidates[0].parameter_domain["candidate_profile"], "stabilize_first")


if __name__ == "__main__":
    unittest.main()
