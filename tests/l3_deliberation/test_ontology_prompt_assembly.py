"""PR-Β Slice 2: SalienceSpec + DlpfcRoleContract + ScenarioOntology + build_dlpfc_system_prompt.

Tests cover:
- SalienceSpec is a frozen text container with format_text()
- DlpfcRoleContract is a frozen text container with format_text()
- ScenarioOntology bundles 5 framework components + optional world_facts_fn
- build_dlpfc_system_prompt(scenario_ontology) assembles the 6-section system
  prompt with the canonical headers per plan §5.3

Red lines:
- Headers must be exactly: ``=== EVA dlPFC Role ===`` / ``=== Drive Ontology ===``
  / ``=== Salience Spec ===`` / ``=== Action Ontology ===`` /
  ``=== Action Effect Schema ===`` / ``=== Crafter World Facts ===``
  (last is scenario-customizable, but slot is fixed)
- world_facts_fn=None must not break assembly; just skips section.
"""

from __future__ import annotations

import unittest


class SalienceSpecTests(unittest.TestCase):
    def test_format_text_returns_provided_body(self) -> None:
        from eva.l3_deliberation.ontology import SalienceSpec
        spec = SalienceSpec(body="salience body text")
        self.assertEqual(spec.format_text(), "salience body text")

    def test_spec_is_frozen(self) -> None:
        from eva.l3_deliberation.ontology import SalienceSpec
        spec = SalienceSpec(body="x")
        with self.assertRaises(Exception):
            spec.body = "y"  # type: ignore[misc]


class DlpfcRoleContractTests(unittest.TestCase):
    def test_format_text_returns_provided_body(self) -> None:
        from eva.l3_deliberation.ontology import DlpfcRoleContract
        contract = DlpfcRoleContract(body="role contract body")
        self.assertEqual(contract.format_text(), "role contract body")


class ScenarioOntologyTests(unittest.TestCase):
    def test_construction_with_all_components(self) -> None:
        from eva.l3_deliberation.ontology import (
            ActionEffectSchema,
            ActionOntology,
            ActionOntologyEntry,
            DlpfcRoleContract,
            DriveOntology,
            DriveOntologyEntry,
            SalienceSpec,
            ScenarioOntology,
        )
        drives = DriveOntology(entries=(
            DriveOntologyEntry(name="metabolic", meaning="m", low_means="l",
                               high_means="h", typical_causes=[], relief_directions=[]),
        ))
        actions = ActionOntology(entries=(
            ActionOntologyEntry(action="do", effect="ctx", details=[]),
        ))
        effects = ActionEffectSchema(matrix={"do": {"metabolic": "context_dependent"}})
        salience = SalienceSpec(body="salience text")
        role = DlpfcRoleContract(body="role text")

        ont = ScenarioOntology(
            scenario_name="crafter",
            dlpfc_role_contract=role,
            drive_ontology=drives,
            salience_spec=salience,
            action_ontology=actions,
            action_effect_schema=effects,
            world_facts_fn=lambda: "facts",
        )
        self.assertEqual(ont.scenario_name, "crafter")
        self.assertIs(ont.drive_ontology, drives)
        self.assertIs(ont.action_ontology, actions)
        self.assertIs(ont.action_effect_schema, effects)
        self.assertEqual(ont.world_facts_fn(), "facts")


class BuildDlpfcSystemPromptTests(unittest.TestCase):
    def _mk(self, *, world_facts_fn=None):
        from eva.l3_deliberation.ontology import (
            ActionEffectSchema, ActionOntology, ActionOntologyEntry,
            DlpfcRoleContract, DriveOntology, DriveOntologyEntry,
            SalienceSpec, ScenarioOntology,
        )
        return ScenarioOntology(
            scenario_name="crafter",
            dlpfc_role_contract=DlpfcRoleContract(body="ROLE BODY"),
            drive_ontology=DriveOntology(entries=(
                DriveOntologyEntry(name="metabolic", meaning="MEANING-M",
                                   low_means="L", high_means="H",
                                   typical_causes=[], relief_directions=[]),
            )),
            salience_spec=SalienceSpec(body="SALIENCE BODY"),
            action_ontology=ActionOntology(entries=(
                ActionOntologyEntry(action="do", effect="EFFECT-DO", details=[]),
            )),
            action_effect_schema=ActionEffectSchema(matrix={
                "do": {"metabolic": "context_dependent"},
            }),
            world_facts_fn=world_facts_fn,
        )

    def test_assembly_contains_six_canonical_headers(self) -> None:
        from eva.l3_deliberation.ontology import build_dlpfc_system_prompt
        ont = self._mk(world_facts_fn=lambda: "WORLD FACTS BODY")
        text = build_dlpfc_system_prompt(ont)
        # Six section headers
        self.assertIn("=== EVA dlPFC Role ===", text)
        self.assertIn("=== Drive Ontology ===", text)
        self.assertIn("=== Salience Spec ===", text)
        self.assertIn("=== Action Ontology ===", text)
        self.assertIn("=== Action Effect Schema ===", text)
        self.assertIn("=== Crafter World Facts ===", text)
        # Each body
        self.assertIn("ROLE BODY", text)
        self.assertIn("MEANING-M", text)
        self.assertIn("SALIENCE BODY", text)
        self.assertIn("EFFECT-DO", text)
        self.assertIn("context_dependent", text)
        self.assertIn("WORLD FACTS BODY", text)

    def test_assembly_without_world_facts_skips_section(self) -> None:
        from eva.l3_deliberation.ontology import build_dlpfc_system_prompt
        ont = self._mk(world_facts_fn=None)
        text = build_dlpfc_system_prompt(ont)
        # Other 5 sections still present
        self.assertIn("=== EVA dlPFC Role ===", text)
        self.assertIn("=== Drive Ontology ===", text)
        # No World Facts header / body
        self.assertNotIn("=== Crafter World Facts ===", text)

    def test_assembly_sections_in_canonical_order(self) -> None:
        from eva.l3_deliberation.ontology import build_dlpfc_system_prompt
        ont = self._mk(world_facts_fn=lambda: "facts")
        text = build_dlpfc_system_prompt(ont)
        idx_role = text.find("=== EVA dlPFC Role ===")
        idx_drive = text.find("=== Drive Ontology ===")
        idx_salience = text.find("=== Salience Spec ===")
        idx_action = text.find("=== Action Ontology ===")
        idx_effect = text.find("=== Action Effect Schema ===")
        idx_world = text.find("=== Crafter World Facts ===")
        # Order per plan §5.3
        self.assertLess(idx_role, idx_drive)
        self.assertLess(idx_drive, idx_salience)
        self.assertLess(idx_salience, idx_action)
        self.assertLess(idx_action, idx_effect)
        self.assertLess(idx_effect, idx_world)

    def test_world_facts_header_uses_scenario_name(self) -> None:
        """World facts header should be ``=== {ScenarioName} World Facts ===``."""
        from eva.l3_deliberation.ontology import build_dlpfc_system_prompt, ScenarioOntology
        from eva.l3_deliberation.ontology import (
            ActionEffectSchema, ActionOntology, DlpfcRoleContract,
            DriveOntology, SalienceSpec,
        )
        # Custom scenario name "linux" should produce "=== Linux World Facts ==="
        ont = ScenarioOntology(
            scenario_name="linux",
            dlpfc_role_contract=DlpfcRoleContract(body="role"),
            drive_ontology=DriveOntology(entries=()),
            salience_spec=SalienceSpec(body="sal"),
            action_ontology=ActionOntology(entries=()),
            action_effect_schema=ActionEffectSchema(matrix={}),
            world_facts_fn=lambda: "linux facts",
        )
        text = build_dlpfc_system_prompt(ont)
        self.assertIn("=== Linux World Facts ===", text)


if __name__ == "__main__":
    unittest.main()
