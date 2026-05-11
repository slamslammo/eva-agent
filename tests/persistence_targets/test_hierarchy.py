from __future__ import annotations

import unittest

from eva.persistence_targets import (
    PersistenceHierarchy,
    PersistenceTarget,
    build_linux_runtime_persistence_hierarchy,
    get_default_persistence_hierarchy,
)
import eva.persistence_targets as persistence_targets


class PersistenceHierarchyTests(unittest.TestCase):
    def test_linux_runtime_hierarchy_activates_level_1_and_level_4(self) -> None:
        hierarchy = build_linux_runtime_persistence_hierarchy()

        self.assertEqual([target.level for target in hierarchy.active_targets()], [1, 4])
        self.assertEqual(hierarchy.target_for_level(1).name, "substrate_instance")
        self.assertEqual(hierarchy.target_for_level(4).dependencies, (1,))

    def test_hierarchy_reports_failed_and_at_risk_targets(self) -> None:
        hierarchy = build_linux_runtime_persistence_hierarchy()

        failed = hierarchy.failed_targets({"instance_valid": False})
        at_risk = hierarchy.targets_at_risk({"instance_valid": False})

        self.assertEqual([target.level for target in failed], [1])
        self.assertEqual([target.level for target in at_risk], [4])
        self.assertEqual(hierarchy.dependency_failures({"instance_valid": False}), {4: (1,)})

    def test_local_unrecoverable_failure_requires_transfer_channel(self) -> None:
        hierarchy = PersistenceHierarchy(
            targets=(
                PersistenceTarget(level=1, name="substrate_instance", failure_condition=lambda context: not bool(context.get("instance_valid", False))),
                PersistenceTarget(level=2, name="successor_backed_target", failure_condition=lambda context: False, transfer_channel="handoff"),
            )
        )

        self.assertTrue(hierarchy.local_unrecoverable_failure_forbidden(1))
        self.assertFalse(hierarchy.local_unrecoverable_failure_forbidden(2))
        self.assertFalse(hierarchy.can_locally_authorize_unrecoverable_failure(1))
        self.assertTrue(hierarchy.can_locally_authorize_unrecoverable_failure(2))

    def test_default_hierarchy_lookup_requires_registration(self) -> None:
        original = persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY
        persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY = None
        try:
            with self.assertRaisesRegex(RuntimeError, "no persistence hierarchy registered"):
                get_default_persistence_hierarchy()
        finally:
            persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY = original


if __name__ == "__main__":
    unittest.main()
