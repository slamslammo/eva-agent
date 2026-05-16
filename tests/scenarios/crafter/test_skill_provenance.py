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
            self.assertIn("source_paths", record.provenance.scope)
            self.assertIn("related_anchor_profiles", record.provenance.scope)
            self.assertIn(record.provenance.provenance_detail, {
                "crafter_safety_escalation_prior",
                "crafter_safety_stabilization_floor_prior",
                "crafter_metabolic_stabilization_prior",
                "crafter_metabolic_recognition_prior",
                "crafter_recovery_rest_prior",
                "crafter_recovery_recognition_prior",
                "crafter_acquisition_resource_chain_prior",
                "crafter_acquisition_survival_floor_prior",
                "crafter_capability_resource_chain_prior",
                "crafter_capability_survival_floor_prior",
                "crafter_action_surface_baseline_prior",
            })


if __name__ == "__main__":
    unittest.main()
