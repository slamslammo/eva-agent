from __future__ import annotations

import unittest

from eva.anchor.domain_restriction import build_action_domain
from eva.l3_deliberation import build_deliberation_input, build_candidates
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.anchors import build_crafter_action_domain


MOVE_ACTIONS = {"move_left", "move_right", "move_up", "move_down"}


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

    def _observation(
        self,
        *,
        health: int = 9,
        food: int = 7,
        water: int = 7,
        energy: int = 8,
        cells: list[list[str]] | None = None,
        inventory: dict[str, int] | None = None,
        facing: str = "left",
    ) -> dict[str, object]:
        return {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "ep",
            "step": 1,
            "visible": {
                "life_panel": {
                    "values": {"health": health, "food": food, "water": water, "energy": energy}
                },
                "inventory_panel": {"items": inventory or {}},
                "facing": facing,
                "local_view": {
                    "format": "semantic_grid",
                    "width": 3,
                    "height": 3,
                    "center": {"row": 1, "col": 1},
                    "cells": cells or [
                        ["grass", "grass", "grass"],
                        ["grass", "player", "grass"],
                        ["grass", "grass", "grass"],
                    ],
                },
            },
        }

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

    def test_raw_anchor_water_critical_admits_unordered_movement_set_only(self) -> None:
        deliberation_input = self._base_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.9,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="water_critical",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(
            agent_state,
            self._observation(
                water=2,
                facing="left",
                cells=[
                    ["grass", "water", "grass"],
                    ["grass", "player", "grass"],
                    ["grass", "grass", "grass"],
                ],
            ),
        )

        self.assertEqual(domain.action_set, MOVE_ACTIONS)
        self.assertNotIn("do", domain.action_set)
        self.assertNotIn("sleep", domain.action_set)
        self.assertNotIn("noop", domain.action_set)
        self.assertIn("water_critical_move_set", domain.restriction_reasons)

    def test_raw_anchor_water_not_visible_still_does_not_choose_direction(self) -> None:
        deliberation_input = self._base_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.9,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="water_critical",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(agent_state, self._observation(water=2))

        self.assertEqual(domain.action_set, MOVE_ACTIONS)

    def test_raw_anchor_food_critical_does_not_turn_facing_food_into_do(self) -> None:
        deliberation_input = self._base_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.9,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="food_critical",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(
            agent_state,
            self._observation(
                food=2,
                facing="right",
                cells=[
                    ["grass", "grass", "grass"],
                    ["grass", "player", "cow"],
                    ["grass", "grass", "plant"],
                ],
            ),
        )

        self.assertEqual(domain.action_set, MOVE_ACTIONS)
        self.assertNotIn("do", domain.action_set)
        self.assertIn("food_critical_move_set", domain.restriction_reasons)

    def test_raw_anchor_threat_visible_admits_move_set_plus_do(self) -> None:
        deliberation_input = self._base_input(
            top_drive="safety",
            drive_levels={
                "metabolic": 0.1,
                "safety": 0.9,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="health_critical",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(
            agent_state,
            self._observation(
                health=2,
                cells=[
                    ["grass", "grass", "grass"],
                    ["grass", "player", "zombie"],
                    ["grass", "grass", "grass"],
                ],
            ),
        )

        self.assertEqual(domain.action_set, MOVE_ACTIONS | {"do"})
        self.assertIn("threat_response_move_or_do_set", domain.restriction_reasons)

    def test_raw_anchor_energy_critical_without_threat_admits_sleep_only(self) -> None:
        deliberation_input = self._base_input(
            top_drive="recovery",
            drive_levels={
                "metabolic": 0.1,
                "safety": 0.1,
                "recovery": 0.9,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            pressure_reason="energy_critical",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(agent_state, self._observation(energy=2))

        self.assertEqual(domain.action_set, {"sleep"})
        self.assertIn("energy_critical_sleep_set", domain.restriction_reasons)

    def test_raw_anchor_normal_domain_is_feasible_raw_actions_without_strategy_keys(self) -> None:
        deliberation_input = self._base_input(
            top_drive="acquisition",
            drive_levels={
                "metabolic": 0.2,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.4,
                "capability": 0.1,
            },
            pressure_reason="inventory_sparse",
        )
        agent_state = build_action_domain(deliberation_input).agent_state

        domain = build_crafter_action_domain(
            agent_state,
            self._observation(
                inventory={"wood": 1},
                cells=[
                    ["table", "grass", "grass"],
                    ["grass", "player", "grass"],
                    ["grass", "grass", "grass"],
                ],
            ),
        )

        self.assertIn("do", domain.action_set)
        self.assertIn("make_wood_pickaxe", domain.action_set)
        self.assertNotIn("place_table", domain.action_set)
        self.assertIn("normal_feasible_raw_set", domain.restriction_reasons)
        serialized = domain.to_dict()
        # anchor-domain-chain-trace: to_dict now also carries trace-only chain
        # fields (feasible_actions / gate_branch). The test's intent — A'(s) must
        # NOT leak strategy/ordering keys — is unchanged and re-asserted below.
        self.assertEqual(
            set(serialized),
            {"action_set", "restriction_reasons", "feasible_actions", "gate_branch"},
        )
        flattened_keys = set(serialized)
        for value in serialized.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        flattened_keys.update(item)
            elif isinstance(value, dict):
                flattened_keys.update(value)
        self.assertFalse({"rank", "preferred_action", "score", "direction_hint"} & flattened_keys)


if __name__ == "__main__":
    unittest.main()
