from __future__ import annotations

import unittest

from scenarios.crafter.wrapper import build_symbolic_observation, validate_agent_local_view


class CrafterFairnessContractTests(unittest.TestCase):
    def test_symbolic_observation_does_not_expose_forbidden_keys(self) -> None:
        observation = build_symbolic_observation(
            episode_id="episode-1",
            step=0,
            raw_observation=[[0]],
            raw_info={
                "semantic": [[1]],
                "player_pos": [10, 20],
                "inventory": {"wood": 1},
                "life": {"health": 5, "food": 7, "water": 6, "energy": 8},
            },
        )
        validation = validate_agent_local_view(observation)
        self.assertTrue(validation["passed"])
        self.assertNotIn("semantic", observation)
        self.assertNotIn("player_pos", observation)
        self.assertNotIn("position", observation)


if __name__ == "__main__":
    unittest.main()
