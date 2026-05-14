from __future__ import annotations

import unittest

from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.prior_skills import prior_skill_registry


class CrafterSkillProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_prior_records_carry_crafter_provenance(self) -> None:
        registry = prior_skill_registry(top_drive="safety", life_state="STABLE", pressure_reason="health_critical")
        records = registry.records()
        self.assertGreaterEqual(len(records), 1)
        for record in records:
            self.assertEqual(record.provenance.source, "scenario")
            self.assertEqual(record.provenance.scope["scenario"], "crafter")
            self.assertIn(record.provenance.provenance_detail, {
                "crafter_runtime_survival_prior",
                "crafter_runtime_recognition_prior",
                "crafter_runtime_resource_chain_prior",
                "crafter_runtime_action_semantics",
            })


if __name__ == "__main__":
    unittest.main()
