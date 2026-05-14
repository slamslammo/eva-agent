"""Crafter prior-skill surfaces for Stage H H-4."""

from .compatibility import (
    PRIOR_SKILL_MATCH_PROFILES,
    build_situation_key_from_values,
    derive_habit_skills,
    habit_skill_match_for_candidate_profile,
    prior_skill_registry,
    situation_key_from_learning_outcome,
    summarize_habit_bias,
)

__all__ = [
    "PRIOR_SKILL_MATCH_PROFILES",
    "build_situation_key_from_values",
    "derive_habit_skills",
    "habit_skill_match_for_candidate_profile",
    "prior_skill_registry",
    "situation_key_from_learning_outcome",
    "summarize_habit_bias",
]
