"""single-source-linux-drive-metadata — Linux drive preset derivation equivalence.

LINUX_DRIVE_SPEC (engine-only — Linux is rule-driven, no dlPFC ontology) becomes
the single authority; the Linux drive_preset's identity fields (drive_types /
drive_type_by_dimension / curiosity_drive_type) derive from it. Pins byte/semantic
equivalence to the pre-refactor hardcoded values captured in
_linux_drive_spec_oracle.json (snapshot on 4c029e0, the pre-refactor code) — per
the anti-circular red line (oracle from OLD code).

DriveUpdatePolicy stays authored on the preset (behavior, not identity), same as
the Crafter single-source split.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

_ORACLE = json.loads((Path(__file__).parent / "_linux_drive_spec_oracle.json").read_text())


class LinuxDriveSpecEquivalenceTests(unittest.TestCase):
    def test_spec_exists_and_is_single_source(self) -> None:
        from eva.l3_deliberation.ontology import ScenarioDriveSpec
        from scenarios.linux_runtime.drive_preset import LINUX_DRIVE_SPEC

        self.assertIsInstance(LINUX_DRIVE_SPEC, ScenarioDriveSpec)
        self.assertTrue(LINUX_DRIVE_SPEC.version)

    def test_derived_drive_types_match_oracle(self) -> None:
        from scenarios.linux_runtime.drive_preset import LINUX_RUNTIME_DRIVE_PRESET

        self.assertEqual(list(LINUX_RUNTIME_DRIVE_PRESET.drive_types), _ORACLE["drive_types"])

    def test_derived_dimension_map_match_oracle(self) -> None:
        from scenarios.linux_runtime.drive_preset import LINUX_RUNTIME_DRIVE_PRESET

        self.assertEqual(
            LINUX_RUNTIME_DRIVE_PRESET.drive_type_by_dimension,
            _ORACLE["drive_type_by_dimension"],
        )

    def test_derived_curiosity_match_oracle(self) -> None:
        from scenarios.linux_runtime.drive_preset import LINUX_RUNTIME_DRIVE_PRESET

        self.assertEqual(
            LINUX_RUNTIME_DRIVE_PRESET.curiosity_drive_type, _ORACLE["curiosity_drive_type"]
        )

    def test_single_source_derivation_holds(self) -> None:
        from scenarios.linux_runtime.drive_preset import (
            LINUX_DRIVE_SPEC,
            LINUX_RUNTIME_DRIVE_PRESET,
        )

        self.assertEqual(
            tuple(LINUX_RUNTIME_DRIVE_PRESET.drive_types), LINUX_DRIVE_SPEC.drive_types()
        )
        self.assertEqual(
            LINUX_RUNTIME_DRIVE_PRESET.drive_type_by_dimension,
            LINUX_DRIVE_SPEC.drive_type_by_dimension(),
        )
        self.assertEqual(
            LINUX_RUNTIME_DRIVE_PRESET.curiosity_drive_type,
            LINUX_DRIVE_SPEC.curiosity_drive_type(),
        )

    def test_linux_spec_has_no_llm_semantics(self) -> None:
        # Linux is engine-only: no drive ontology. The spec entries carry no
        # LLM semantic text (meaning empty) — and thus cannot build an ontology.
        from scenarios.linux_runtime.drive_preset import LINUX_DRIVE_SPEC

        for e in LINUX_DRIVE_SPEC.entries:
            self.assertEqual(e.meaning, "")
        with self.assertRaises(ValueError):
            LINUX_DRIVE_SPEC.build_drive_ontology()


if __name__ == "__main__":
    unittest.main()
