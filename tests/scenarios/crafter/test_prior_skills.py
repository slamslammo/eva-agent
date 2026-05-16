from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.prior_skills import (
    CRAFTER_STARTUP_PRIOR_DEFINITIONS,
    PRIOR_SKILL_MATCH_PROFILES,
    build_crafter_inherited_prior_registry,
    build_crafter_startup_prior_registry,
    build_situation_key_from_values,
    derive_habit_skills,
    habit_skill_match_for_candidate_profile,
    prior_skill_registry,
    summarize_habit_bias,
)


class CrafterPriorSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_build_situation_key_uses_crafter_values(self) -> None:
        self.assertEqual(
            build_situation_key_from_values(
                top_drive="metabolic",
                life_state="STABLE",
                pressure_reason="water_critical",
            ),
            "metabolic|STABLE|water_critical",
        )

    def test_prior_match_profiles_are_bounded_to_existing_candidate_profiles(self) -> None:
        self.assertEqual(PRIOR_SKILL_MATCH_PROFILES, frozenset({"observe_first", "stabilize_first", "escalate_first"}))
        self.assertTrue(habit_skill_match_for_candidate_profile("observe_first"))
        self.assertFalse(habit_skill_match_for_candidate_profile("unknown"))

    def test_prior_registry_projects_survival_priors_to_stabilize_first(self) -> None:
        registry = prior_skill_registry(top_drive="metabolic", life_state="STABLE", pressure_reason="water_critical")
        records = registry.records()
        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(records[0].candidate_profile, "stabilize_first")
        self.assertEqual(records[0].preferred_action, "do")

    def test_summarize_habit_bias_and_derive_habit_skills_keep_crafter_profiles(self) -> None:
        learning_outcomes = [
            {
                "recorded_at": "2026-05-13T00:00:00Z",
                "candidate_profile": "stabilize_first",
                "selected_action": "sleep",
                "outcome_delta": 1.0,
                "content": {
                    "top_drive": "recovery",
                    "life_state": "STABLE",
                    "pressure_reason": "energy_critical",
                    "situation_key": "recovery|STABLE|energy_critical",
                },
            }
        ]
        summaries = summarize_habit_bias(learning_outcomes, situation_key="recovery|STABLE|energy_critical")
        self.assertEqual(summaries[0]["candidate_profile"], "stabilize_first")
        skills = derive_habit_skills(
            situation_key="recovery|STABLE|energy_critical",
            learning_outcomes=learning_outcomes,
        )
        self.assertEqual(skills[0]["candidate_profile"], "stabilize_first")


    def test_startup_prior_registry_exposes_canonical_bundle(self) -> None:
        registry = build_crafter_startup_prior_registry()
        records = registry.records()

        self.assertEqual(len(records), len(CRAFTER_STARTUP_PRIOR_DEFINITIONS))
        self.assertTrue(all(record.provenance.source == "scenario" for record in records))
        self.assertTrue(all(record.provenance.scope["scenario"] == "crafter" for record in records))
        self.assertTrue(all("source_paths" in record.provenance.scope for record in records))
        self.assertTrue(all(record.situation_key.startswith("crafter_startup_prior|") for record in records))

    def test_crafter_inherited_prior_registry_loads_valid_bundle(self) -> None:
        bundle = {
            "scenario": "crafter",
            "distillation_date": "2026-05-15T00:00:00Z",
            "records": [
                {
                    "confidence": 0.84,
                    "content": {
                        "situation_key": "metabolic|STABLE|water_critical",
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
                        "avoid_action": "do",
                        "evidence_count": 5,
                        "stability_score": 0.8,
                        "bias_strength": 0.6,
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "DistilledPriorBundle.json"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            registry = build_crafter_inherited_prior_registry(bundle_path)

        records = registry.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].candidate_profile, "stabilize_first")
        self.assertEqual(records[0].preferred_action, "sleep")
        self.assertEqual(records[0].provenance.scope["scenario"], "crafter")

    def test_crafter_inherited_prior_registry_rejects_invalid_scenario_bundle(self) -> None:
        bundle = {
            "scenario": "linux_runtime",
            "records": [
                {
                    "confidence": 0.84,
                    "content": {
                        "situation_key": "metabolic|STABLE|water_critical",
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
                        "evidence_count": 5,
                        "stability_score": 0.8,
                        "bias_strength": 0.6,
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "DistilledPriorBundle.json"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "crafter"):
                build_crafter_inherited_prior_registry(bundle_path)


if __name__ == "__main__":
    unittest.main()
