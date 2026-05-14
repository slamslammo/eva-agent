from __future__ import annotations

import unittest

from eva.persistence_targets import get_default_persistence_hierarchy
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.persistence import build_crafter_persistence_hierarchy


class CrafterPersistenceHierarchyTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_crafter_hierarchy_activates_levels_1_to_4(self) -> None:
        hierarchy = build_crafter_persistence_hierarchy()
        self.assertEqual([target.level for target in hierarchy.active_targets()], [1, 2, 3, 4])
        self.assertEqual(hierarchy.target_for_level(2).name, "crafter_avatar_instance")
        self.assertEqual(hierarchy.target_for_level(3).dependencies, (1, 2))
        self.assertEqual(hierarchy.target_for_level(4).dependencies, (1, 2))

    def test_level_2_failure_marks_levels_3_and_4_at_risk(self) -> None:
        hierarchy = build_crafter_persistence_hierarchy()
        failed = hierarchy.failed_targets({"instance_valid": True, "avatar_health": 0})
        at_risk = hierarchy.targets_at_risk({"instance_valid": True, "avatar_health": 0})
        self.assertEqual([target.level for target in failed], [2])
        self.assertEqual([target.level for target in at_risk], [3, 4])

    def test_crafter_activation_registers_crafter_hierarchy(self) -> None:
        hierarchy = get_default_persistence_hierarchy()
        self.assertEqual([target.level for target in hierarchy.active_targets()], [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
