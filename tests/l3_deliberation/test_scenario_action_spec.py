"""single-source-crafter-action-metadata slice 1 — ScenarioActionSpec framework type.

Mirrors ScenarioDriveSpec (the drive single-source done in the prior task):
a scenario's action *identity + semantics* live in one declaration, from which
both the raw-action name tuple (ALL_ACTIONS) and the ActionOntology are derived,
so the two can no longer drift apart.

Unlike drives, raw actions carry no engine-side mapping fields (a drive has
``dimensions``); an action is just a name + its LLM-facing semantics
(effect / details / typical_use). slice 1 fixes the framework type only;
Crafter adoption lands in slice 2.
"""

from __future__ import annotations

import dataclasses
import unittest

from eva.l3_deliberation.ontology import (
    ActionOntology,
    ActionSpecEntry,
    ScenarioActionSpec,
)


def _spec() -> ScenarioActionSpec:
    return ScenarioActionSpec(
        version="test-v1",
        entries=(
            ActionSpecEntry(
                action="noop",
                effect="skip turn",
                details=(),
                typical_use="rarely useful",
            ),
            ActionSpecEntry(
                action="move_left",
                effect="move 1 left",
                details=("passable: move", "water: refill"),
            ),
            ActionSpecEntry(
                action="do",
                effect="context-sensitive",
                details=("facing tree: collect wood",),
            ),
        ),
    )


class ActionSpecEntryTests(unittest.TestCase):
    def test_entry_is_frozen(self) -> None:
        e = ActionSpecEntry(action="x", effect="e")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            e.action = "y"  # type: ignore[misc]

    def test_entry_defaults(self) -> None:
        e = ActionSpecEntry(action="x", effect="e")
        self.assertEqual(e.details, ())
        self.assertIsNone(e.typical_use)


class ScenarioActionSpecDerivationTests(unittest.TestCase):
    def test_action_names_preserve_declaration_order(self) -> None:
        self.assertEqual(_spec().action_names(), ("noop", "move_left", "do"))

    def test_build_action_ontology_derives_matching_entries(self) -> None:
        ont = _spec().build_action_ontology()
        self.assertIsInstance(ont, ActionOntology)
        self.assertEqual(ont.actions(), frozenset({"noop", "move_left", "do"}))
        noop = ont.get("noop")
        assert noop is not None
        self.assertEqual(noop.effect, "skip turn")
        self.assertEqual(noop.typical_use, "rarely useful")
        self.assertEqual(tuple(noop.details), ())
        ml = ont.get("move_left")
        assert ml is not None
        self.assertEqual(tuple(ml.details), ("passable: move", "water: refill"))
        self.assertIsNone(ml.typical_use)

    def test_build_action_ontology_preserves_entry_order(self) -> None:
        ont = _spec().build_action_ontology()
        self.assertEqual(tuple(e.action for e in ont.entries), ("noop", "move_left", "do"))

    def test_single_source_invariant_names_equal_action_names(self) -> None:
        spec = _spec()
        self.assertEqual(spec.build_action_ontology().actions(), frozenset(spec.action_names()))

    def test_spec_is_frozen(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
            _spec().version = "other"  # type: ignore[misc]

    def test_duplicate_action_name_raises(self) -> None:
        # Action names must be unique — declaring the same action twice is a
        # construction error (ambiguous ontology / name set).
        bad = ScenarioActionSpec(
            version="v",
            entries=(
                ActionSpecEntry(action="dup", effect="a"),
                ActionSpecEntry(action="dup", effect="b"),
            ),
        )
        with self.assertRaises(ValueError):
            bad.action_names()


if __name__ == "__main__":
    unittest.main()
