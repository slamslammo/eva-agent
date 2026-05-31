"""single-source-linux-drive-metadata — DriveSpecEntry engine-only support.

A G1 decision (plan §10) option (a)+guard: a scenario like Linux that is
rule-driven (no dlPFC, no drive ontology) adopts ScenarioDriveSpec for ONLY the
engine fields (drive_types / dimension-map / curiosity). To allow that, the LLM
semantic fields (meaning / low_means / high_means) become optional (default '').

Guard: build_drive_ontology() must NOT silently emit an empty-semantics ontology
— if any entry has an empty meaning it raises, so an engine-only spec can never
be mistaken for an ontology source. Crafter (all fields filled) is unaffected.
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.ontology import DriveSpecEntry, ScenarioDriveSpec


class EngineOnlyFieldDefaultsTests(unittest.TestCase):
    def test_llm_semantic_fields_default_empty(self) -> None:
        # Engine-only: only name (+ optionally dimensions/is_curiosity) supplied.
        e = DriveSpecEntry(name="survival")
        self.assertEqual(e.meaning, "")
        self.assertEqual(e.low_means, "")
        self.assertEqual(e.high_means, "")

    def test_engine_only_spec_derives_identity(self) -> None:
        spec = ScenarioDriveSpec(
            version="engine-only-test",
            entries=(
                DriveSpecEntry(name="survival", dimensions=("resource_state",)),
                DriveSpecEntry(name="curiosity", is_curiosity=True),
            ),
        )
        self.assertEqual(spec.drive_types(), ("survival", "curiosity"))
        self.assertEqual(spec.drive_type_by_dimension(), {"resource_state": "survival"})
        self.assertEqual(spec.curiosity_drive_type(), "curiosity")


class BuildOntologyGuardTests(unittest.TestCase):
    def test_build_drive_ontology_raises_on_empty_meaning(self) -> None:
        # The guard: an engine-only spec (empty meaning) must NOT yield a silent
        # empty-semantics ontology — building one is a programming error.
        spec = ScenarioDriveSpec(
            version="engine-only-test",
            entries=(DriveSpecEntry(name="survival", dimensions=("resource_state",)),),
        )
        with self.assertRaises(ValueError):
            spec.build_drive_ontology()

    def test_build_drive_ontology_ok_when_all_meanings_filled(self) -> None:
        # Crafter-style: all semantic fields filled → ontology builds fine.
        spec = ScenarioDriveSpec(
            version="full",
            entries=(
                DriveSpecEntry(name="metabolic", meaning="m", low_means="l", high_means="h"),
            ),
        )
        ont = spec.build_drive_ontology()
        self.assertEqual(ont.names(), frozenset({"metabolic"}))


if __name__ == "__main__":
    unittest.main()
