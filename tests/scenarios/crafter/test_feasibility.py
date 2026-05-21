"""Round 1.I (a2): Crafter per-turn action feasibility filter.

Pins World-layer feasibility (drop only physically-impossible actions per Crafter's
recipes) and the red-line that always-feasible actions are NEVER dropped (no usefulness
filtering), so every posture keeps at least its default and the set is never empty.
"""

from __future__ import annotations

import unittest

from scenarios.crafter.actions.compatibility import PROFILE_DEFAULT_ACTION, PROFILE_ELIGIBLE_ACTIONS
from scenarios.crafter.actions.feasibility import action_is_feasible, feasible_profile_action_vocab


def _obs(inventory: dict, cells: list[list[str]] | None = None) -> dict:
    return {
        "visible": {
            "inventory_panel": {"items": inventory},
            "local_view": {"cells": cells or [["grass", "grass"], ["grass", "grass"]]},
        }
    }


class FeasibilityTests(unittest.TestCase):
    def test_make_iron_filtered_without_materials_or_furnace(self) -> None:
        vocab = feasible_profile_action_vocab(_obs({"wood": 5}))
        esc = vocab["escalate_first"]
        self.assertNotIn("make_iron_pickaxe", esc)  # no coal/iron, no furnace
        self.assertNotIn("make_iron_sword", esc)

    def test_make_wood_pickaxe_needs_wood_and_nearby_table(self) -> None:
        # wood present but no table in view -> infeasible.
        self.assertNotIn("make_wood_pickaxe", feasible_profile_action_vocab(_obs({"wood": 1}))["escalate_first"])
        # wood present AND table in view -> feasible.
        with_table = feasible_profile_action_vocab(_obs({"wood": 1}, cells=[["table", "grass"]]))
        self.assertIn("make_wood_pickaxe", with_table["escalate_first"])
        # iron tools still filtered (no iron/coal/furnace) even with a table.
        self.assertNotIn("make_iron_pickaxe", with_table["escalate_first"])

    def test_place_actions_gate_on_inventory(self) -> None:
        self.assertNotIn("place_table", feasible_profile_action_vocab(_obs({"wood": 1}))["escalate_first"])  # needs 2
        self.assertIn("place_table", feasible_profile_action_vocab(_obs({"wood": 2}))["escalate_first"])
        self.assertNotIn("place_furnace", feasible_profile_action_vocab(_obs({"stone": 3}))["escalate_first"])  # needs 4
        self.assertIn("place_furnace", feasible_profile_action_vocab(_obs({"stone": 4}))["escalate_first"])

    def test_always_feasible_actions_never_dropped(self) -> None:
        # Empty inventory, barren view: only world-impossible craft/place actions go.
        vocab = feasible_profile_action_vocab(_obs({}))
        self.assertIn("do", vocab["escalate_first"])
        self.assertIn("move_left", vocab["escalate_first"])
        self.assertIn("noop", vocab["observe_first"])
        self.assertIn("sleep", vocab["stabilize_first"])

    def test_filter_only_removes_never_adds_and_keeps_default(self) -> None:
        vocab = feasible_profile_action_vocab(_obs({}))
        for profile, actions in PROFILE_ELIGIBLE_ACTIONS.items():
            self.assertTrue(set(vocab[profile]).issubset(set(actions)))  # only removes
            self.assertIn(PROFILE_DEFAULT_ACTION[profile], vocab[profile])  # never empty
            self.assertTrue(vocab[profile])

    def test_action_is_feasible_pure_helper(self) -> None:
        self.assertTrue(action_is_feasible("do", {}, set()))
        self.assertFalse(action_is_feasible("make_iron_sword", {"wood": 9}, {"table", "furnace"}))  # no iron/coal
        self.assertTrue(action_is_feasible("make_iron_sword", {"wood": 1, "coal": 1, "iron": 1}, {"table", "furnace"}))
        self.assertFalse(action_is_feasible("make_iron_sword", {"wood": 1, "coal": 1, "iron": 1}, {"table"}))  # no furnace


if __name__ == "__main__":
    unittest.main()
