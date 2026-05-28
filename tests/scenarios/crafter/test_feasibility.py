"""Crafter per-turn action feasibility filter (PR-4 update).

Pins World-layer feasibility (drop only physically-impossible actions per Crafter's
recipes) and the red-line that always-feasible actions are NEVER dropped (no usefulness
filtering).
"""

from __future__ import annotations

import unittest

from scenarios.crafter.actions.feasibility import action_is_feasible, feasible_raw_actions


def _obs(inventory: dict, cells: list[list[str]] | None = None) -> dict:
    return {
        "visible": {
            "inventory_panel": {"items": inventory},
            "local_view": {"cells": cells or [["grass", "grass"], ["grass", "grass"]]},
        }
    }


class FeasibilityTests(unittest.TestCase):
    def test_action_is_feasible_pure_helper(self) -> None:
        self.assertTrue(action_is_feasible("do", {}, set()))
        self.assertFalse(action_is_feasible("make_iron_sword", {"wood": 9}, {"table", "furnace"}))  # no iron/coal
        self.assertTrue(action_is_feasible("make_iron_sword", {"wood": 1, "coal": 1, "iron": 1}, {"table", "furnace"}))
        self.assertFalse(action_is_feasible("make_iron_sword", {"wood": 1, "coal": 1, "iron": 1}, {"table"}))  # no furnace

    def test_feasible_raw_actions_filters_only_world_impossible_actions(self) -> None:
        actions = feasible_raw_actions(_obs({"wood": 1}, cells=[["table", "grass"]]))

        self.assertIn("noop", actions)
        self.assertIn("move_left", actions)
        self.assertIn("move_right", actions)
        self.assertIn("move_up", actions)
        self.assertIn("move_down", actions)
        self.assertIn("do", actions)
        self.assertIn("sleep", actions)
        self.assertIn("make_wood_pickaxe", actions)
        self.assertNotIn("place_table", actions)  # needs wood x2
        self.assertNotIn("make_iron_sword", actions)  # needs iron/coal/furnace

    def test_feasible_raw_actions_always_feasible_never_dropped(self) -> None:
        # Empty inventory, barren view: only world-impossible craft/place actions go.
        actions = feasible_raw_actions(_obs({}))
        self.assertIn("do", actions)
        self.assertIn("noop", actions)
        self.assertIn("sleep", actions)
        self.assertIn("move_left", actions)

    def test_feasible_raw_actions_make_iron_needs_materials_and_furnace(self) -> None:
        actions = feasible_raw_actions(_obs({"wood": 5}))
        self.assertNotIn("make_iron_pickaxe", actions)
        self.assertNotIn("make_iron_sword", actions)

    def test_feasible_raw_actions_make_wood_needs_table(self) -> None:
        # wood present but no table in view -> infeasible
        without_table = feasible_raw_actions(_obs({"wood": 1}))
        self.assertNotIn("make_wood_pickaxe", without_table)

        # wood present AND table in view -> feasible
        with_table = feasible_raw_actions(_obs({"wood": 1}, cells=[["table", "grass"]]))
        self.assertIn("make_wood_pickaxe", with_table)

    def test_feasible_raw_actions_place_gates_on_inventory(self) -> None:
        self.assertNotIn("place_table", feasible_raw_actions(_obs({"wood": 1})))  # needs 2
        self.assertIn("place_table", feasible_raw_actions(_obs({"wood": 2})))


if __name__ == "__main__":
    unittest.main()
