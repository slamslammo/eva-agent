from __future__ import annotations

import unittest

from scenarios.crafter.actions import ACTION_METADATA, CRAFTER_ACTIONS, ActionAdapter
from scenarios.crafter.wrapper import CrafterEnvWrapper, CrafterLoadError, validate_agent_local_view


class CrafterWrapperSmokeTests(unittest.TestCase):
    def test_action_adapter_exposes_expected_17_action_enum(self) -> None:
        self.assertEqual(len(CRAFTER_ACTIONS), 17)
        self.assertEqual(CRAFTER_ACTIONS[0], "noop")
        self.assertEqual(CRAFTER_ACTIONS[-1], "make_iron_sword")
        self.assertEqual(ACTION_METADATA["move_up"]["reversibility"], "high")
        self.assertEqual(ACTION_METADATA["do"]["reversibility"], "medium")
        self.assertEqual(ACTION_METADATA["place_table"]["reversibility"], "low")

    def test_action_adapter_roundtrips_and_reports_action_count(self) -> None:
        adapter = ActionAdapter()
        self.assertEqual(adapter.name_to_id("move_up"), 3)
        self.assertEqual(adapter.id_to_name(3), "move_up")
        report = adapter.validate_env_action_space(type("FakeSpace", (), {"n": 17})())
        self.assertTrue(report["matches_expected"])
        self.assertEqual(report["expected_action_count"], 17)

    def test_wrapper_reset_and_step_produce_agent_observation_when_crafter_installed(self) -> None:
        try:
            wrapper = CrafterEnvWrapper(seed=0)
        except CrafterLoadError as exc:
            self.skipTest(str(exc))
            return

        try:
            observation = wrapper.reset(seed=0)
            self.assertEqual(observation["schema_version"], "symbolic_observation_v0")
            self.assertEqual(observation["step"], 0)
            self.assertEqual(observation["available_actions"], list(CRAFTER_ACTIONS))
            validation = validate_agent_local_view(observation)
            self.assertTrue(validation["passed"])

            step_result = wrapper.step("noop")
            self.assertEqual(step_result.agent_observation["schema_version"], "symbolic_observation_v0")
            self.assertEqual(step_result.agent_observation["step"], 1)
            self.assertIsInstance(step_result.reward, float)
            self.assertIsInstance(step_result.done, bool)
            validation = validate_agent_local_view(step_result.agent_observation)
            self.assertTrue(validation["passed"])
        finally:
            wrapper.close()


    def test_reset_observation_not_blind(self) -> None:
        """Reset frame must have life, inventory, and local_view available (regression guard)."""
        try:
            wrapper = CrafterEnvWrapper(seed=0)
        except CrafterLoadError as exc:
            self.skipTest(str(exc))
            return

        try:
            obs = wrapper.reset(seed=0)
            vis = obs["visible"]

            lp = vis["life_panel"]
            self.assertTrue(lp["available"], "life_panel must be available on reset frame")
            self.assertEqual(lp["values"]["health"], 9)
            self.assertEqual(lp["values"]["food"], 9)
            self.assertIsNotNone(lp["values"]["water"])
            self.assertIsNotNone(lp["values"]["energy"])

            ip = vis["inventory_panel"]
            self.assertTrue(ip["available"], "inventory_panel must be available on reset frame")

            lv = vis["local_view"]
            self.assertEqual(lv["source"], "semantic_local_crop",
                             "local_view must show real grid on reset frame, not _unknown_view")
            self.assertGreater(len(lv["cells"]), 0)
        finally:
            wrapper.close()


if __name__ == "__main__":
    unittest.main()
