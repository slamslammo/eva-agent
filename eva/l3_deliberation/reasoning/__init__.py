"""Reasoning subpackage for candidate assembly, value judgment, and working memory."""

from .candidate_generation import ESCALATE_FIRST_PROFILE, OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE, build_candidates
from .conflict_detection import CandidateConflictContext, build_candidate_conflict_context
from .value_judgment import assess_candidates
from .working_memory import (
    AUTO_WORKING_MEMORY_BACKEND,
    MIN_AUTO_LLM_CONFIDENCE,
    WorkingMemoryContext,
    build_llm_working_memory_context,
    build_situation_key,
    build_working_memory_context,
    build_working_memory_context_from_store,
)
from ..memory.skill_library import HabitBiasSummary, build_situation_key_from_values, summarize_habit_bias

__all__ = [
    "ESCALATE_FIRST_PROFILE",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "AUTO_WORKING_MEMORY_BACKEND",
    "MIN_AUTO_LLM_CONFIDENCE",
    "CandidateConflictContext",
    "HabitBiasSummary",
    "WorkingMemoryContext",
    "build_candidate_conflict_context",
    "build_candidates",
    "assess_candidates",
    "build_llm_working_memory_context",
    "build_situation_key",
    "build_situation_key_from_values",
    "build_working_memory_context",
    "build_working_memory_context_from_store",
    "summarize_habit_bias",
]
