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

    def test_high_metabolic_admits_escalate_first(self) -> None:
        # 修复 B：饥饿 / 缺水（metabolic 高）应 admit escalate，让 agent 能去
        # 采集食物 / 水 —— 而非被强制锁死成 stabilize→sleep（睡觉在 Crafter 里
        # 不恢复 food/water，会让 agent 饿着空跑）。stabilize 仍作为兜底保留。
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
        profiles = [c.parameter_domain["candidate_profile"] for c in candidates]
        self.assertIn("escalate_first", profiles)
        self.assertIn("stabilize_first", profiles)


if __name__ == "__main__":
    unittest.main()
