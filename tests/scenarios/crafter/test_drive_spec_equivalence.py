"""single-source-scenario-drive-metadata slice 2 — Crafter derivation equivalence.

CRAFTER_DRIVE_SPEC becomes the single authority; CRAFTER_DRIVE_PRESET (identity
fields) and CRAFTER_DRIVE_ONTOLOGY are derived from it. This test pins that the
derived values are byte/semantically identical to the pre-refactor hardcoded
values, captured in _drive_spec_oracle.json (snapshot taken on the original
two-source code before slice 2). Behavior tuning (DriveUpdatePolicy) is NOT
covered here — it stays authored on the preset and is checked by the existing
test_drive_preset.py.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

_ORACLE = json.loads((Path(__file__).parent / "_drive_spec_oracle.json").read_text())


class CrafterDriveSpecEquivalenceTests(unittest.TestCase):
    def test_spec_exists_and_is_the_single_source(self) -> None:
        from eva.l3_deliberation.ontology import ScenarioDriveSpec
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_SPEC

        self.assertIsInstance(CRAFTER_DRIVE_SPEC, ScenarioDriveSpec)
        self.assertTrue(CRAFTER_DRIVE_SPEC.version)

    def test_derived_ontology_format_text_byte_identical(self) -> None:
        # The dlPFC prompt section must be byte-for-byte unchanged.
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        self.assertEqual(
            CRAFTER_DRIVE_ONTOLOGY.format_text(), _ORACLE["ontology_format_text"]
        )

    def test_derived_ontology_entries_match_oracle(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        derived = [
            {
                "name": e.name,
                "meaning": e.meaning,
                "low_means": e.low_means,
                "high_means": e.high_means,
                "typical_causes": list(e.typical_causes),
                "relief_directions": list(e.relief_directions),
            }
            for e in CRAFTER_DRIVE_ONTOLOGY.entries
        ]
        self.assertEqual(derived, _ORACLE["entries"])

    def test_derived_preset_drive_types_match_oracle(self) -> None:
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET

        self.assertEqual(
            list(CRAFTER_DRIVE_PRESET.drive_types), _ORACLE["drive_types"]
        )

    def test_derived_preset_dimension_map_match_oracle(self) -> None:
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET

        self.assertEqual(
            CRAFTER_DRIVE_PRESET.drive_type_by_dimension,
            _ORACLE["drive_type_by_dimension"],
        )

    def test_derived_preset_curiosity_match_oracle(self) -> None:
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET

        self.assertEqual(
            CRAFTER_DRIVE_PRESET.curiosity_drive_type, _ORACLE["curiosity_drive_type"]
        )

    def test_single_source_invariant_holds(self) -> None:
        # The whole point: ontology name set == preset drive_types, by construction.
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET
        from scenarios.crafter.ontology import CRAFTER_DRIVE_ONTOLOGY

        self.assertEqual(
            CRAFTER_DRIVE_ONTOLOGY.names(),
            frozenset(CRAFTER_DRIVE_PRESET.drive_types),
        )

    def test_preset_behavior_policy_unchanged(self) -> None:
        # DriveUpdatePolicy (behavior tuning) must survive the refactor untouched
        # — it is authored on the preset, NOT derived from the spec.
        from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET

        policy = CRAFTER_DRIVE_PRESET.default_policy
        self.assertEqual(policy.update_mode, "approach")
        self.assertEqual(policy.approach_rate, 0.3)
        self.assertEqual(policy.target_critical, 0.9)
        self.assertEqual(policy.target_degraded, 0.55)
        self.assertEqual(policy.curiosity_recovery, 0.07)
        self.assertEqual(policy.curiosity_suppression, 0.06)
        self.assertFalse(policy.curiosity_suppress_on_degraded_status)


if __name__ == "__main__":
    unittest.main()
