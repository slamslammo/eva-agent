"""PR-Β §5.5: structural consistency tests for Crafter scenario ontology.

These tests are the **anti-drift guards** required by the plan. They catch:
- drives added/removed in CRAFTER_DRIVE_PRESET but not synced to drive ontology
- raw actions added/removed in ALL_ACTIONS but not synced to action ontology
- missing cells in the action × drive effect matrix (must be 17 × 6 = 102)
- empty required fields in DriveOntologyEntry

Plan §5.5 explicitly requires 4 minimum tests; this file provides each.

These tests catch STRUCTURAL drift (cardinality / field presence). Semantic
drift (meaning text written wrong) is governed by §5.6 process constraints —
B must flag any inconsistency between drive_state implementation and ontology
description rather than silently merging.
"""

from __future__ import annotations

import unittest

from scenarios.crafter import activate_crafter_scenario


class CrafterDriveOntologyConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_drive_ontology_covers_all_preset_drives(self) -> None:
        """CRAFTER_DRIVE_ONTOLOGY.names() must equal CRAFTER_DRIVE_PRESET.drive_types.

        single-source-scenario-drive-metadata: this now holds *by construction*
        — both the ontology and the preset drive_types derive from the same
        CRAFTER_DRIVE_SPEC, so they can no longer drift. Kept as a regression
        guard against anyone re-introducing a parallel hardcoded source (see
        test_both_derive_from_the_same_spec for the structural guarantee).
        """
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        ontology_drives = CRAFTER_DRIVE_ONTOLOGY.names()
        preset_drives = frozenset(CRAFTER_DRIVE_PRESET.drive_types)
        self.assertEqual(
            ontology_drives, preset_drives,
            f"drive ontology / preset mismatch: ontology={ontology_drives} preset={preset_drives}",
        )

    def test_both_derive_from_the_same_spec(self) -> None:
        """Anti-drift root guarantee: ontology and preset come from one spec.

        The name-set equality above is now *structural*, not coincidental: the
        ontology equals ``CRAFTER_DRIVE_SPEC.build_drive_ontology()`` and the
        preset identity fields equal the spec's derivations. If a future change
        re-hardcodes either source independently, these identity checks break.
        """
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET, CRAFTER_DRIVE_SPEC
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        self.assertEqual(
            CRAFTER_DRIVE_ONTOLOGY.names(),
            CRAFTER_DRIVE_SPEC.build_drive_ontology().names(),
        )
        self.assertEqual(
            tuple(CRAFTER_DRIVE_PRESET.drive_types), CRAFTER_DRIVE_SPEC.drive_types()
        )
        self.assertEqual(
            CRAFTER_DRIVE_PRESET.drive_type_by_dimension,
            CRAFTER_DRIVE_SPEC.drive_type_by_dimension(),
        )
        self.assertEqual(
            CRAFTER_DRIVE_PRESET.curiosity_drive_type,
            CRAFTER_DRIVE_SPEC.curiosity_drive_type(),
        )

    def test_drive_ontology_required_fields_non_empty(self) -> None:
        """Each entry must have non-empty meaning / low_means / high_means + ≥1 cause + ≥1 relief direction."""
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        for entry in CRAFTER_DRIVE_ONTOLOGY.entries:
            self.assertTrue(entry.name, f"drive entry has empty name")
            self.assertTrue(entry.meaning, f"drive {entry.name} has empty meaning")
            self.assertTrue(entry.low_means, f"drive {entry.name} has empty low_means")
            self.assertTrue(entry.high_means, f"drive {entry.name} has empty high_means")
            self.assertGreaterEqual(
                len(entry.typical_causes), 1,
                f"drive {entry.name} has empty typical_causes",
            )
            self.assertGreaterEqual(
                len(entry.relief_directions), 1,
                f"drive {entry.name} has empty relief_directions",
            )


class CrafterActionOntologyConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_action_ontology_covers_all_raw_actions(self) -> None:
        """CRAFTER_ACTION_ONTOLOGY.actions() must equal ALL_ACTIONS set."""
        from scenarios.crafter.actions import ALL_ACTIONS
        from scenarios.crafter.ontology import CRAFTER_ACTION_ONTOLOGY

        ontology_actions = CRAFTER_ACTION_ONTOLOGY.actions()
        raw_actions = frozenset(ALL_ACTIONS)
        self.assertEqual(
            ontology_actions, raw_actions,
            f"action ontology / ALL_ACTIONS mismatch: ontology={ontology_actions} raw={raw_actions}",
        )

    def test_action_ontology_required_fields_non_empty(self) -> None:
        """Each action entry must have non-empty effect text."""
        from scenarios.crafter.ontology import CRAFTER_ACTION_ONTOLOGY

        for entry in CRAFTER_ACTION_ONTOLOGY.entries:
            self.assertTrue(entry.action, "action entry has empty action name")
            self.assertTrue(entry.effect, f"action {entry.action} has empty effect")


class CrafterActionEffectSchemaConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_action_effect_schema_covers_17_x_6_cells(self) -> None:
        """The effect schema must have a cell for every action × drive combination."""
        from scenarios.crafter.actions import ALL_ACTIONS
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET
        from scenarios.crafter.ontology import CRAFTER_ACTION_EFFECT_SCHEMA

        actions = list(ALL_ACTIONS)
        drives = list(CRAFTER_DRIVE_PRESET.drive_types)
        self.assertEqual(len(actions) * len(drives), 17 * 6)

        missing: list[str] = []
        for action in actions:
            for drive in drives:
                if CRAFTER_ACTION_EFFECT_SCHEMA.effect(action, drive) is None:
                    missing.append(f"{action} × {drive}")
        self.assertEqual(
            missing, [],
            f"effect schema missing {len(missing)} cells: {missing[:5]}{'...' if len(missing) > 5 else ''}",
        )

    def test_effect_schema_actions_match_all_actions(self) -> None:
        from scenarios.crafter.actions import ALL_ACTIONS
        from scenarios.crafter.ontology import CRAFTER_ACTION_EFFECT_SCHEMA
        self.assertEqual(CRAFTER_ACTION_EFFECT_SCHEMA.actions(), frozenset(ALL_ACTIONS))

    def test_effect_schema_drives_match_preset_drives(self) -> None:
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET
        from scenarios.crafter.ontology import CRAFTER_ACTION_EFFECT_SCHEMA
        self.assertEqual(
            CRAFTER_ACTION_EFFECT_SCHEMA.drives(),
            frozenset(CRAFTER_DRIVE_PRESET.drive_types),
        )


class CrafterScenarioOntologyExportTests(unittest.TestCase):
    """The scenario package must export a single CRAFTER_SCENARIO_ONTOLOGY entry point."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_scenario_ontology_bundle_exposed(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY

        self.assertEqual(CRAFTER_SCENARIO_ONTOLOGY.scenario_name, "crafter")
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.drive_ontology)
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.action_ontology)
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.action_effect_schema)
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.salience_spec)
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.dlpfc_role_contract)
        # world_facts_fn should be wired to scenario's existing world facts module.
        self.assertIsNotNone(CRAFTER_SCENARIO_ONTOLOGY.world_facts_fn)


class CrafterDlpfcRoleContractContentTests(unittest.TestCase):
    """§5.4.3 red line: contract must include allowed observation channel (canary)."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_role_contract_mentions_allowed_observation_channel(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        # Plan §5.4.3 explicit requirement: "allowed observation channel"
        # is the dlPFC canary. Body must reference it semantically.
        self.assertTrue(
            "observation" in body.lower() or "金丝雀" in body or "canary" in body.lower(),
            "role contract must include the allowed observation channel (canary)",
        )

    def test_role_contract_lists_dlpfc_position_in_chain(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        # Must position dlPFC between anchor and OFC.
        self.assertIn("anchor", body)
        self.assertIn("OFC", body)
        self.assertIn("mediator", body)


if __name__ == "__main__":
    unittest.main()
