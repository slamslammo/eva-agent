from __future__ import annotations
import tempfile
import unittest
from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input, build_learning_outcome_record, evaluate_response_outcome
from eva.l3_deliberation.memory import derive_habit_skills, summarize_habit_bias
from eva.l3_deliberation.memory.skill_library import habit_skill_registry, inherited_prior_registry, prior_skill_registry
from eva.l3_deliberation.reasoning import build_working_memory_context, build_working_memory_context_from_store
from eva.l3_deliberation.memory import (
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
)
from eva.l3_deliberation.memory import (
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_HEURISTIC,
    NullWorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    WorkingMemoryModelClientResponse,
    build_builtin_working_memory_model_client,
)
from scenarios.linux_runtime import activate_linux_runtime_scenario
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE


class SkillLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_derive_habit_skills_requires_repeated_hit_counts_for_crystallization(self) -> None:
        skills = derive_habit_skills(
            situation_key="integrity|STABLE|recent_yield_detected",
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 4,
                    "habit_skill_hit_count": 2,
                    "habit_narrowed_count": 1,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.75,
                }
            ],
        )

        self.assertEqual(len(skills), 1)
        self.assertFalse(skills[0].crystallized)
        self.assertIn("insufficient_habit_hits", skills[0].crystallization_reasons)
        self.assertIn("insufficient_effective_hits", skills[0].crystallization_reasons)

    def test_derive_habit_skills_degrades_after_recent_negative_streak(self) -> None:
        skills = derive_habit_skills(
            situation_key="integrity|STABLE|recent_yield_detected",
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 5,
                    "habit_skill_hit_count": 4,
                    "habit_narrowed_count": 2,
                    "recent_negative_count": 2,
                    "last_outcome_delta": -0.5,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.4,
                }
            ],
        )

        self.assertEqual(len(skills), 1)
        self.assertFalse(skills[0].crystallized)
        self.assertIn("recent_negative_streak", skills[0].crystallization_reasons)
        self.assertIn("last_outcome_negative", skills[0].crystallization_reasons)

    def test_derive_habit_skills_keeps_weak_bias_non_crystallized(self) -> None:
        skills = derive_habit_skills(
            situation_key="integrity|STABLE|recent_yield_detected",
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 2,
                    "habit_skill_hit_count": 2,
                    "habit_narrowed_count": 0,
                    "stability_score": 0.4,
                    "confidence": 0.45,
                    "bias_strength": 0.4,
                }
            ],
        )

        self.assertEqual(len(skills), 1)
        self.assertFalse(skills[0].crystallized)
        self.assertIn("insufficient_evidence", skills[0].crystallization_reasons)
        self.assertIn("insufficient_stability", skills[0].crystallization_reasons)
        self.assertIn("insufficient_confidence", skills[0].crystallization_reasons)


    def test_prior_skill_registry_exposes_scenario_owned_records_with_provenance(self) -> None:
        registry = prior_skill_registry(situation_key="integrity|STABLE|recent_yield_detected")

        records = registry.records()
        self.assertGreaterEqual(len(records), 3)
        self.assertTrue(all(record.provenance.source == "scenario" for record in records))
        self.assertTrue(all(record.provenance.mutable is False for record in records))
        self.assertEqual(records[0].provenance.scope["situation_key"], "integrity|STABLE|recent_yield_detected")

    def test_habit_skill_registry_wraps_experience_derived_records_with_provenance(self) -> None:
        registry = habit_skill_registry(
            situation_key="integrity|STABLE|recent_yield_detected",
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 5,
                    "habit_skill_hit_count": 4,
                    "habit_narrowed_count": 1,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.75,
                }
            ],
        )

        records = registry.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].provenance.source, "experience")
        self.assertTrue(records[0].provenance.mutable)
        self.assertEqual(records[0].provenance.scope["situation_key"], "integrity|STABLE|recent_yield_detected")

    def test_inherited_prior_registry_remains_placeholder(self) -> None:
        registry = inherited_prior_registry()

        self.assertEqual(registry.records(), [])
        with self.assertRaisesRegex(NotImplementedError, "reserved for v0.7\+"):
            registry.register({"candidate_profile": "observe_first"})

