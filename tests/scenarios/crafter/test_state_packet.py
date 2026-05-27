from __future__ import annotations

import unittest

from scenarios.crafter.state_packet import SCHEMA_VERSION, build_crafter_state_packet


class CrafterStatePacketTests(unittest.TestCase):
    def _observation(self) -> dict[str, object]:
        return {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "episode-1",
            "step": 4,
            "visible": {
                "life_panel": {
                    "values": {"health": 9, "food": 7, "water": 2, "energy": 8}
                },
                "inventory_panel": {"items": {"wood": 1, "stone": 0}},
                "facing": "left",
                "local_view": {
                    "format": "semantic_grid",
                    "width": 3,
                    "height": 3,
                    "center": {"row": 1, "col": 1},
                    "cells": [
                        ["grass", "water", "grass"],
                        ["tree", "player", "cow"],
                        ["grass", "zombie", "plant"],
                    ],
                },
            },
            "available_actions": ["noop", "move_left", "do"],
        }

    def test_state_packet_carries_auditable_perception_without_strategy_fields(self) -> None:
        packet = build_crafter_state_packet(
            self._observation(),
            drive_broadcast={
                "top_drive": "metabolic",
                "drive_levels": {"metabolic": 0.9},
                "drive_trends": {"metabolic": "worsening"},
            },
            working_memory_context={
                "rates": {"water_delta_recent": -3},
                "recent_relevant_outcomes": [
                    {"selected_action": "do", "pressure_outcome": "unchanged"}
                ],
            },
            available_actions=("noop", "move_left", "do"),
        )

        self.assertEqual(packet["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            packet["raw_observation_ref"],
            "symbolic_observation_v0:episode=episode-1:step=4",
        )
        self.assertEqual(packet["life"]["water"], 2.0)
        self.assertEqual(packet["facing"], "left")
        self.assertEqual(packet["inventory"], {"wood": 1, "stone": 0})
        self.assertEqual(packet["local_view"]["cells"][0][1], "water")
        self.assertEqual(packet["visible"]["water"][0]["offset"], {"row": -1, "col": 0})
        self.assertEqual({item["kind"] for item in packet["visible"]["food"]}, {"cow", "plant"})
        self.assertEqual(packet["visible"]["threats"][0]["kind"], "zombie")
        self.assertEqual(packet["salience"]["thirst"], "critical")
        self.assertEqual(packet["salience"]["top_drive"], "metabolic")
        self.assertEqual(packet["rates"]["water_delta_recent"], -3.0)
        self.assertEqual(packet["recent_outcomes"], ["do -> unchanged"])
        self.assertEqual(packet["available_actions"], ["noop", "move_left", "do"])
        self.assertEqual(packet["world_facts_ref"], "crafter_world_facts_v1")

        flattened_keys = set()
        self._collect_keys(packet, flattened_keys)
        self.assertFalse(
            {"preferred_action", "direction_hint", "rank", "score", "target_action"}
            & flattened_keys
        )

    def test_state_packet_allows_explicit_raw_observation_ref(self) -> None:
        packet = build_crafter_state_packet(
            self._observation(),
            raw_observation_ref="raw_observations/turn-00000004.json",
        )

        self.assertEqual(packet["raw_observation_ref"], "raw_observations/turn-00000004.json")

    def _collect_keys(self, value: object, out: set[str]) -> None:
        if isinstance(value, dict):
            out.update(str(key) for key in value)
            for item in value.values():
                self._collect_keys(item, out)
        elif isinstance(value, list):
            for item in value:
                self._collect_keys(item, out)


if __name__ == "__main__":
    unittest.main()
