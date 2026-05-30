"""single-source-scenario-drive-metadata slice 1 — ScenarioDriveSpec framework type.

ScenarioDriveSpec is the single structured authority source for a scenario's
drive *identity / semantics*. DrivePreset's drive identity (drive_types,
drive_type_by_dimension, curiosity_drive_type) and the DriveOntology are both
DERIVED from it, so the two can no longer drift apart. Behavior tuning
(DriveUpdatePolicy) stays in the preset and is out of scope here.

slice 1 fixes only the framework type + its derivation methods. Crafter
adoption lands in slice 2.
"""

from __future__ import annotations

import dataclasses
import unittest

from eva.l3_deliberation.ontology import (
    DriveOntology,
    DriveSpecEntry,
    ScenarioDriveSpec,
)


def _spec() -> ScenarioDriveSpec:
    return ScenarioDriveSpec(
        version="test-v1",
        entries=(
            DriveSpecEntry(
                name="metabolic",
                meaning="m-meaning",
                low_means="m-low",
                high_means="m-high",
                typical_causes=("c1", "c2"),
                relief_directions=("r1",),
                dimensions=("avatar_metabolic",),
            ),
            DriveSpecEntry(
                name="safety",
                meaning="s-meaning",
                low_means="s-low",
                high_means="s-high",
                typical_causes=("c3",),
                relief_directions=("r2",),
                # one drive bound to multiple sensor dimensions
                dimensions=("avatar_safety", "local_view_threat"),
            ),
            DriveSpecEntry(
                name="exploration",
                meaning="e-meaning",
                low_means="e-low",
                high_means="e-high",
                typical_causes=("c4",),
                relief_directions=("r3",),
                # internal drive: no sensor dimensions, curiosity-updated
                dimensions=(),
                is_curiosity=True,
            ),
        ),
    )


class DriveSpecEntryTests(unittest.TestCase):
    def test_entry_is_frozen(self) -> None:
        e = DriveSpecEntry(name="x", meaning="m", low_means="l", high_means="h")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            e.name = "y"  # type: ignore[misc]

    def test_entry_defaults(self) -> None:
        e = DriveSpecEntry(name="x", meaning="m", low_means="l", high_means="h")
        self.assertEqual(e.typical_causes, ())
        self.assertEqual(e.relief_directions, ())
        self.assertEqual(e.dimensions, ())
        self.assertFalse(e.is_curiosity)


class ScenarioDriveSpecDerivationTests(unittest.TestCase):
    def test_drive_types_preserves_declaration_order(self) -> None:
        self.assertEqual(_spec().drive_types(), ("metabolic", "safety", "exploration"))

    def test_drive_type_by_dimension_inverts_dimensions(self) -> None:
        # Each dimension maps to its owning drive; a drive with multiple
        # dimensions expands to multiple entries; dimensionless drives are absent.
        self.assertEqual(
            _spec().drive_type_by_dimension(),
            {
                "avatar_metabolic": "metabolic",
                "avatar_safety": "safety",
                "local_view_threat": "safety",
            },
        )

    def test_curiosity_drive_type_returns_the_flagged_drive(self) -> None:
        self.assertEqual(_spec().curiosity_drive_type(), "exploration")

    def test_curiosity_drive_type_none_when_unflagged(self) -> None:
        spec = ScenarioDriveSpec(
            version="v",
            entries=(DriveSpecEntry(name="a", meaning="m", low_means="l", high_means="h"),),
        )
        self.assertIsNone(spec.curiosity_drive_type())

    def test_multiple_curiosity_drives_raises(self) -> None:
        # The framework's curiosity update path targets exactly one drive type;
        # declaring two is a construction error, not silent first-wins.
        bad = ScenarioDriveSpec(
            version="v",
            entries=(
                DriveSpecEntry(name="a", meaning="m", low_means="l", high_means="h", is_curiosity=True),
                DriveSpecEntry(name="b", meaning="m", low_means="l", high_means="h", is_curiosity=True),
            ),
        )
        with self.assertRaises(ValueError):
            bad.curiosity_drive_type()

    def test_build_drive_ontology_derives_matching_entries(self) -> None:
        ont = _spec().build_drive_ontology()
        self.assertIsInstance(ont, DriveOntology)
        # name set agrees with drive_types (this is the anti-drift guarantee)
        self.assertEqual(ont.names(), frozenset({"metabolic", "safety", "exploration"}))
        m = ont.get("metabolic")
        assert m is not None
        self.assertEqual(m.meaning, "m-meaning")
        self.assertEqual(m.low_means, "m-low")
        self.assertEqual(m.high_means, "m-high")
        self.assertEqual(tuple(m.typical_causes), ("c1", "c2"))
        self.assertEqual(tuple(m.relief_directions), ("r1",))

    def test_build_drive_ontology_preserves_entry_order(self) -> None:
        ont = _spec().build_drive_ontology()
        self.assertEqual(
            tuple(e.name for e in ont.entries), ("metabolic", "safety", "exploration")
        )

    def test_ontology_names_equal_drive_types_set(self) -> None:
        # The single-source invariant: derived ontology and derived preset
        # drive_types can never disagree because both come from spec.entries.
        spec = _spec()
        self.assertEqual(spec.build_drive_ontology().names(), frozenset(spec.drive_types()))

    def test_spec_is_frozen(self) -> None:
        spec = _spec()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            spec.version = "other"  # type: ignore[misc]

    def test_duplicate_dimension_across_drives_raises(self) -> None:
        # A sensor dimension must map to exactly one drive; declaring the same
        # dimension on two drives is a construction-time error (not silent
        # last-wins), since drive_type_by_dimension would be ambiguous.
        bad = ScenarioDriveSpec(
            version="v",
            entries=(
                DriveSpecEntry(name="a", meaning="m", low_means="l", high_means="h",
                               dimensions=("shared_dim",)),
                DriveSpecEntry(name="b", meaning="m", low_means="l", high_means="h",
                               dimensions=("shared_dim",)),
            ),
        )
        with self.assertRaises(ValueError):
            bad.drive_type_by_dimension()


if __name__ == "__main__":
    unittest.main()
