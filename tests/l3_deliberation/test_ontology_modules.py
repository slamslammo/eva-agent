"""PR-Β: framework ontology module dataclass tests.

Tests cover:
- DriveOntologyEntry + DriveOntology container
- ActionOntologyEntry + ActionOntology container
- ActionEffectSchema (semantic mapping of action × drive → effect label)
- Each dataclass is frozen, lookup helpers work, text format helpers produce
  human-readable output.

Red lines (plan §5):
- effect label vocabulary is the semantic set
  (improves / worsens / neutral / context_dependent / improves_if_* /
   worsens_if_* / time_passes)
- 不带程度副词的归纳估值（"slightly worsens", "often improves" 不能出现）
"""

from __future__ import annotations

import unittest


class DriveOntologyEntryTests(unittest.TestCase):
    def test_entry_construction_and_field_access(self) -> None:
        from eva.l3_deliberation.ontology import DriveOntologyEntry

        entry = DriveOntologyEntry(
            name="metabolic",
            meaning="生理资源压强",
            low_means="充足",
            high_means="短缺",
            typical_causes=["food 下降", "water 下降"],
            relief_directions=["走进 water tile"],
        )
        self.assertEqual(entry.name, "metabolic")
        self.assertEqual(entry.meaning, "生理资源压强")
        self.assertEqual(list(entry.typical_causes), ["food 下降", "water 下降"])
        self.assertEqual(list(entry.relief_directions), ["走进 water tile"])

    def test_entry_is_frozen_immutable(self) -> None:
        from eva.l3_deliberation.ontology import DriveOntologyEntry

        entry = DriveOntologyEntry(
            name="safety", meaning="m", low_means="l", high_means="h",
            typical_causes=[], relief_directions=[],
        )
        with self.assertRaises(Exception):
            entry.name = "other"  # type: ignore[misc]


class DriveOntologyTests(unittest.TestCase):
    def test_container_lookup_by_name(self) -> None:
        from eva.l3_deliberation.ontology import DriveOntology, DriveOntologyEntry

        e1 = DriveOntologyEntry(name="metabolic", meaning="m1", low_means="l", high_means="h",
                                typical_causes=[], relief_directions=[])
        e2 = DriveOntologyEntry(name="safety", meaning="m2", low_means="l", high_means="h",
                                typical_causes=[], relief_directions=[])
        ont = DriveOntology(entries=(e1, e2))
        self.assertEqual(ont.get("metabolic"), e1)
        self.assertEqual(ont.get("safety"), e2)
        self.assertIsNone(ont.get("nonexistent"))

    def test_names_returns_drive_name_set(self) -> None:
        from eva.l3_deliberation.ontology import DriveOntology, DriveOntologyEntry

        e1 = DriveOntologyEntry(name="metabolic", meaning="m", low_means="l", high_means="h",
                                typical_causes=[], relief_directions=[])
        e2 = DriveOntologyEntry(name="safety", meaning="m", low_means="l", high_means="h",
                                typical_causes=[], relief_directions=[])
        ont = DriveOntology(entries=(e1, e2))
        self.assertEqual(ont.names(), frozenset({"metabolic", "safety"}))

    def test_format_text_contains_all_entry_names_and_meanings(self) -> None:
        from eva.l3_deliberation.ontology import DriveOntology, DriveOntologyEntry

        e = DriveOntologyEntry(
            name="metabolic", meaning="生理资源压强",
            low_means="充足", high_means="短缺",
            typical_causes=["food 下降"], relief_directions=["走进 water tile"],
        )
        ont = DriveOntology(entries=(e,))
        text = ont.format_text()
        self.assertIn("metabolic", text)
        self.assertIn("生理资源压强", text)
        self.assertIn("food 下降", text)
        self.assertIn("走进 water tile", text)


class ActionOntologyEntryTests(unittest.TestCase):
    def test_entry_construction(self) -> None:
        from eva.l3_deliberation.ontology import ActionOntologyEntry

        entry = ActionOntologyEntry(
            action="move_left",
            effect="朝左移动 1 格",
            details=["若目标 tile 是 water：进入并补水"],
        )
        self.assertEqual(entry.action, "move_left")
        self.assertEqual(entry.effect, "朝左移动 1 格")
        self.assertEqual(list(entry.details), ["若目标 tile 是 water：进入并补水"])


class ActionOntologyTests(unittest.TestCase):
    def test_container_lookup_and_actions_set(self) -> None:
        from eva.l3_deliberation.ontology import ActionOntology, ActionOntologyEntry

        e1 = ActionOntologyEntry(action="noop", effect="跳过", details=[])
        e2 = ActionOntologyEntry(action="do", effect="context-sensitive", details=[])
        ont = ActionOntology(entries=(e1, e2))
        self.assertEqual(ont.get("noop"), e1)
        self.assertEqual(ont.get("do"), e2)
        self.assertEqual(ont.actions(), frozenset({"noop", "do"}))

    def test_format_text_contains_action_names_and_effects(self) -> None:
        from eva.l3_deliberation.ontology import ActionOntology, ActionOntologyEntry

        e = ActionOntologyEntry(action="sleep", effect="恢复 energy",
                                details=["不补 food/water/health", "睡眠时易受威胁"])
        ont = ActionOntology(entries=(e,))
        text = ont.format_text()
        self.assertIn("sleep", text)
        self.assertIn("恢复 energy", text)
        self.assertIn("不补 food/water/health", text)


class ActionEffectSchemaTests(unittest.TestCase):
    """Action × drive matrix using semantic effect labels."""

    def test_schema_lookup_returns_label(self) -> None:
        from eva.l3_deliberation.ontology import ActionEffectSchema

        matrix = {
            "move_left": {
                "metabolic": "context_dependent",
                "safety": "context_dependent",
                "exploration": "improves",
            },
        }
        schema = ActionEffectSchema(matrix=matrix)
        self.assertEqual(schema.effect("move_left", "metabolic"), "context_dependent")
        self.assertEqual(schema.effect("move_left", "exploration"), "improves")

    def test_schema_actions_and_drives_views(self) -> None:
        from eva.l3_deliberation.ontology import ActionEffectSchema

        matrix = {
            "noop": {"metabolic": "time_passes", "safety": "time_passes"},
            "do":   {"metabolic": "context_dependent", "safety": "context_dependent"},
        }
        schema = ActionEffectSchema(matrix=matrix)
        self.assertEqual(schema.actions(), frozenset({"noop", "do"}))
        self.assertEqual(schema.drives(), frozenset({"metabolic", "safety"}))

    def test_schema_missing_cell_returns_none(self) -> None:
        from eva.l3_deliberation.ontology import ActionEffectSchema

        schema = ActionEffectSchema(matrix={"do": {"metabolic": "context_dependent"}})
        self.assertIsNone(schema.effect("do", "safety"))
        self.assertIsNone(schema.effect("noop", "metabolic"))

    def test_schema_format_text_contains_cells(self) -> None:
        from eva.l3_deliberation.ontology import ActionEffectSchema

        schema = ActionEffectSchema(matrix={
            "move_left": {"metabolic": "context_dependent", "exploration": "improves"},
        })
        text = schema.format_text()
        self.assertIn("move_left", text)
        self.assertIn("metabolic", text)
        self.assertIn("context_dependent", text)
        self.assertIn("improves", text)


class EffectLabelVocabularyTests(unittest.TestCase):
    """§5.4.5 红线: only semantic labels allowed; no graded adverbs."""

    def test_canonical_label_set_exposed(self) -> None:
        from eva.l3_deliberation.ontology import EFFECT_LABEL_VOCABULARY

        # Core semantic labels per plan §5.4.5
        self.assertIn("improves", EFFECT_LABEL_VOCABULARY)
        self.assertIn("worsens", EFFECT_LABEL_VOCABULARY)
        self.assertIn("neutral", EFFECT_LABEL_VOCABULARY)
        self.assertIn("context_dependent", EFFECT_LABEL_VOCABULARY)
        self.assertIn("time_passes", EFFECT_LABEL_VOCABULARY)


if __name__ == "__main__":
    unittest.main()
