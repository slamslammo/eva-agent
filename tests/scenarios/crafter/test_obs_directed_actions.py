"""Fix-B：观测定向动作解析（escalate 接近 + 面朝即交互）冻结测试。

验证 build_integrity_response_candidates 在拿到 agent_observation 时，会让
escalate_first 朝最近的有用目标走、或在面朝目标时优先 do；拿不到观测时退回旧行为。
"""

from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, RuntimeState, utc_now
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import build_integrity_response_candidates


def _grass_grid(rows: int = 7, cols: int = 9) -> list[list[str]]:
    return [["grass" for _ in range(cols)] for _ in range(rows)]


def _observation(cells: list[list[str]], *, facing: str, center=(3, 4)) -> dict:
    return {
        "visible": {
            "local_view": {
                "cells": cells,
                "center": {"row": center[0], "col": center[1]},
                "width": len(cells[0]),
                "height": len(cells),
            },
            "facing": facing,
        }
    }


def _pressure(reason: str) -> ActivePressure:
    return ActivePressure(
        pressure_id="pressure-1",
        type="integrity",
        severity="degraded",
        evidence={"reason": reason},
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        trend="worsening",
    )


class ObsDirectedActionTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def _escalate_actions(self, observation: dict, reason: str) -> list[str]:
        candidates = build_integrity_response_candidates(
            _pressure(reason),
            RuntimeState(life_state="STABLE", instance_valid=True),
            candidate_context={
                "agent_observation": observation,
                "candidate_profile": "escalate_first",
            },
        )
        return [candidate.action for candidate in candidates]

    def test_escalate_steps_toward_a_distant_target(self) -> None:
        cells = _grass_grid()
        cells[3][6] = "cow"  # +2 columns east of the player center (3,4)
        actions = self._escalate_actions(_observation(cells, facing="down"), "metabolic_degraded")
        # Not facing the cow (facing down) → approach it; move is the first
        # (un-biased tie-break) candidate.
        self.assertEqual(actions[0], "move_right")
        self.assertNotIn("do", actions[:1])

    def test_escalate_interacts_when_facing_the_target(self) -> None:
        cells = _grass_grid()
        cells[3][5] = "cow"  # one tile east; facing right ⇒ facing the cow
        actions = self._escalate_actions(_observation(cells, facing="right"), "metabolic_degraded")
        self.assertEqual(actions[0], "do")

    def test_escalate_prefers_threat_target_under_threat_pressure(self) -> None:
        cells = _grass_grid()
        cells[1][4] = "zombie"  # 2 tiles north (row 1 vs center row 3)
        actions = self._escalate_actions(_observation(cells, facing="down"), "threat_visible")
        self.assertEqual(actions[0], "move_up")

    def test_no_visible_target_falls_back_to_blind_do(self) -> None:
        actions = self._escalate_actions(_observation(_grass_grid(), facing="down"), "metabolic_degraded")
        # No target in view → no observation-directed move; pressure-driven
        # default ``do`` still leads.
        self.assertEqual(actions[0], "do")

    def test_obs_blind_path_is_unchanged_without_observation(self) -> None:
        # No candidate_context → candidate generation stays observation-blind
        # (legacy behavior preserved for the assessment stage).
        candidates = build_integrity_response_candidates(
            _pressure("inventory_sparse"),
            RuntimeState(life_state="STABLE", instance_valid=True),
        )
        escalate = [c.action for c in candidates if c.posture == "crafter_candidate_escalate"]
        self.assertEqual(escalate[0], "do")
        self.assertNotIn("move_right", escalate)


if __name__ == "__main__":
    unittest.main()
