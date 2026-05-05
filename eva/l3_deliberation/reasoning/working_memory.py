"""Rule-based and replaceable working-memory adapters for the Phase C learning layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...kernel import StateStore
from ..contracts import DeliberationInput
from ..memory.episodic import read_cognitive_memory_stub, read_habit_bias, read_learning_outcomes
from ..memory.retrieval import (
    latest_habit_bias_summaries,
    pressure_reason_from_input,
    recent_cognitive_memory_stub_traces,
    recent_learning_outcomes,
    recent_response_history,
)
from ..memory.skill_library import (
    HabitBiasSummary,
    build_situation_key_from_values,
    derive_habit_skills,
    summarize_habit_bias,
)
from ..memory.working_memory_adapter import (
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
)

AUTO_WORKING_MEMORY_BACKEND = "auto"
MIN_AUTO_LLM_CONFIDENCE = 0.6


@dataclass(frozen=True)
class WorkingMemoryContext:
    """Replaceable Phase C working-memory payload read by L3."""

    situation_key: str
    bias_summaries: list[dict[str, Any]] = field(default_factory=list)
    habit_skills: list[dict[str, Any]] = field(default_factory=list)
    recent_relevant_outcomes: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    source_backend: str = "local_rule_based"
    advisory_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the working-memory context payload."""

        return {
            "situation_key": self.situation_key,
            "bias_summaries": [dict(summary) for summary in self.bias_summaries],
            "habit_skills": [dict(skill) for skill in self.habit_skills],
            "recent_relevant_outcomes": [dict(outcome) for outcome in self.recent_relevant_outcomes],
            "confidence": self.confidence,
            "source_backend": self.source_backend,
            "advisory_context": dict(self.advisory_context),
        }


def build_situation_key(deliberation_input: DeliberationInput) -> str:
    """Build the compact recurring-situation key for one deliberation input."""

    return build_situation_key_from_values(
        top_drive=str(deliberation_input.drive_broadcast.get("top_drive") or "unknown"),
        life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
        pressure_reason=pressure_reason_from_input(deliberation_input),
    )


def build_working_memory_context(
    deliberation_input: DeliberationInput,
    *,
    learning_outcomes: list[dict[str, Any]],
    habit_bias_entries: list[dict[str, Any]] | None = None,
    response_history: list[dict[str, Any]] | None = None,
    memory_stubs: list[dict[str, Any]] | None = None,
    max_bias_summaries: int = 2,
    max_habit_skills: int = 2,
    max_recent_outcomes: int = 3,
) -> WorkingMemoryContext:
    """Build a compact working-memory context from local append-only artifacts."""

    situation_key = build_situation_key(deliberation_input)
    matching_habit_bias = [
        dict(entry)
        for entry in (habit_bias_entries or [])
        if str(entry.get("situation_key") or "") == situation_key
    ]
    if matching_habit_bias:
        bias_summaries = latest_habit_bias_summaries(
            matching_habit_bias,
            max_bias_summaries=max_bias_summaries,
        )
    else:
        bias_summaries = [
            summary.to_dict()
            for summary in summarize_habit_bias(learning_outcomes, situation_key=situation_key)[:max_bias_summaries]
        ]
    habit_skill_objects = derive_habit_skills(
        situation_key=situation_key,
        habit_bias_entries=matching_habit_bias,
        learning_outcomes=learning_outcomes,
    )
    habit_skills = [skill.to_dict() for skill in habit_skill_objects[:max_habit_skills]]
    skill_by_profile = {skill.candidate_profile: skill for skill in habit_skill_objects}
    for summary in bias_summaries:
        candidate_profile = str(summary.get("candidate_profile") or "unknown")
        skill = skill_by_profile.get(candidate_profile)
        if skill is None:
            summary["habit_eligible"] = False
            summary["habit_eligibility_reasons"] = ["no_matching_skill_summary"]
            continue
        summary["habit_eligible"] = bool(skill.crystallized)
        summary["habit_eligibility_reasons"] = list(skill.crystallization_reasons)
    top_drive = str(deliberation_input.drive_broadcast.get("top_drive") or "unknown")
    life_state = str(deliberation_input.runtime_gate_context.get("life_state") or "unknown")
    pressure_reason = pressure_reason_from_input(deliberation_input)
    drive_levels = deliberation_input.drive_broadcast.get("drive_levels")
    normalized_drive_levels = dict(drive_levels) if isinstance(drive_levels, dict) else {}
    recent_outcomes = recent_learning_outcomes(
        learning_outcomes,
        situation_key=situation_key,
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
        limit=max_recent_outcomes,
    )
    if not recent_outcomes:
        recent_outcomes = recent_response_history(
            response_history or [],
            top_drive=top_drive,
            life_state=life_state,
            pressure_reason=pressure_reason,
            limit=max_recent_outcomes,
        )
    if not recent_outcomes:
        recent_outcomes = recent_cognitive_memory_stub_traces(
            memory_stubs or [],
            situation_key=situation_key,
            top_drive=top_drive,
            life_state=life_state,
            pressure_reason=pressure_reason,
            drive_levels=normalized_drive_levels,
            limit=max_recent_outcomes,
        )
    top_bias_confidence = max((float(summary.get("confidence", 0.0)) for summary in bias_summaries), default=0.0)
    confidence = min(1.0, max(top_bias_confidence, 0.2 * len(recent_outcomes)))
    return WorkingMemoryContext(
        situation_key=situation_key,
        bias_summaries=bias_summaries,
        habit_skills=habit_skills,
        recent_relevant_outcomes=recent_outcomes,
        confidence=round(confidence, 3),
        source_backend="local_rule_based",
        advisory_context={},
    )


def build_llm_working_memory_context(
    deliberation_input: DeliberationInput,
    *,
    learning_outcomes: list[dict[str, Any]],
    habit_bias_entries: list[dict[str, Any]] | None = None,
    response_history: list[dict[str, Any]] | None = None,
    memory_stubs: list[dict[str, Any]] | None = None,
    llm_adapter: WorkingMemoryAdapter,
    max_bias_summaries: int = 2,
    max_habit_skills: int = 2,
    max_recent_outcomes: int = 3,
) -> WorkingMemoryContext:
    """Build working memory through the local path, then attach bounded llm advisory context."""

    local_context = build_working_memory_context(
        deliberation_input,
        learning_outcomes=learning_outcomes,
        habit_bias_entries=habit_bias_entries,
        response_history=response_history,
        memory_stubs=memory_stubs,
        max_bias_summaries=max_bias_summaries,
        max_habit_skills=max_habit_skills,
        max_recent_outcomes=max_recent_outcomes,
    )
    advisory_context = _sanitize_llm_advisory_context(
        llm_adapter.build_advisory_context(
            WorkingMemoryAdapterRequest(
                situation_key=local_context.situation_key,
                drive_broadcast=dict(deliberation_input.drive_broadcast),
                runtime_gate_context=dict(deliberation_input.runtime_gate_context),
                bias_summaries=[dict(summary) for summary in local_context.bias_summaries],
                habit_skills=[dict(skill) for skill in local_context.habit_skills],
                recent_relevant_outcomes=[dict(outcome) for outcome in local_context.recent_relevant_outcomes],
                local_confidence=local_context.confidence,
            )
        )
    )
    llm_confidence = float(advisory_context.get("confidence", 0.0)) if advisory_context else 0.0
    return WorkingMemoryContext(
        situation_key=local_context.situation_key,
        bias_summaries=[dict(summary) for summary in local_context.bias_summaries],
        habit_skills=[dict(skill) for skill in local_context.habit_skills],
        recent_relevant_outcomes=[dict(outcome) for outcome in local_context.recent_relevant_outcomes],
        confidence=round(max(local_context.confidence, llm_confidence), 3),
        source_backend="llm_assisted",
        advisory_context=advisory_context,
    )


def build_working_memory_context_from_store(
    store: StateStore,
    deliberation_input: DeliberationInput,
    *,
    backend: str = "local_rule_based",
    llm_adapter: WorkingMemoryAdapter | None = None,
    max_bias_summaries: int = 2,
    max_habit_skills: int = 2,
    max_recent_outcomes: int = 3,
    response_history: list[dict[str, Any]] | None = None,
) -> WorkingMemoryContext:
    """Build working-memory context directly from the runtime store."""

    learning_outcomes = read_learning_outcomes(store)
    habit_bias_entries = read_habit_bias(store)
    if response_history is None:
        response_history = store.read_response_history()
    memory_stubs = read_cognitive_memory_stub(store)
    if backend == AUTO_WORKING_MEMORY_BACKEND:
        backend = _select_working_memory_backend(
            deliberation_input,
            learning_outcomes=learning_outcomes,
            habit_bias_entries=habit_bias_entries,
            response_history=response_history,
            memory_stubs=memory_stubs,
            llm_adapter=llm_adapter,
            max_bias_summaries=max_bias_summaries,
            max_habit_skills=max_habit_skills,
            max_recent_outcomes=max_recent_outcomes,
        )
    if backend == "llm_assisted":
        if llm_adapter is None:
            raise ValueError("llm_adapter is required for llm_assisted working-memory backend")
        return build_llm_working_memory_context(
            deliberation_input,
            learning_outcomes=learning_outcomes,
            habit_bias_entries=habit_bias_entries,
            response_history=response_history,
            memory_stubs=memory_stubs,
            llm_adapter=llm_adapter,
            max_bias_summaries=max_bias_summaries,
            max_habit_skills=max_habit_skills,
            max_recent_outcomes=max_recent_outcomes,
        )
    return build_working_memory_context(
        deliberation_input,
        learning_outcomes=learning_outcomes,
        habit_bias_entries=habit_bias_entries,
        response_history=response_history,
        memory_stubs=memory_stubs,
        max_bias_summaries=max_bias_summaries,
        max_habit_skills=max_habit_skills,
        max_recent_outcomes=max_recent_outcomes,
    )


def _select_working_memory_backend(
    deliberation_input: DeliberationInput,
    *,
    learning_outcomes: list[dict[str, Any]],
    habit_bias_entries: list[dict[str, Any]],
    response_history: list[dict[str, Any]],
    memory_stubs: list[dict[str, Any]],
    llm_adapter: WorkingMemoryAdapter | None,
    max_bias_summaries: int,
    max_habit_skills: int,
    max_recent_outcomes: int,
) -> str:
    """Choose a working-memory backend without changing release authority semantics."""

    if llm_adapter is None or isinstance(llm_adapter, NullWorkingMemoryAdapter):
        return "local_rule_based"
    local_context = build_working_memory_context(
        deliberation_input,
        learning_outcomes=learning_outcomes,
        habit_bias_entries=habit_bias_entries,
        response_history=response_history,
        memory_stubs=memory_stubs,
        max_bias_summaries=max_bias_summaries,
        max_habit_skills=max_habit_skills,
        max_recent_outcomes=max_recent_outcomes,
    )
    if _should_prefer_local_working_memory(local_context):
        return "local_rule_based"
    return "llm_assisted"


def _should_prefer_local_working_memory(local_context: WorkingMemoryContext) -> bool:
    """Return whether a stable local habit path should suppress llm usage."""

    if local_context.confidence >= MIN_AUTO_LLM_CONFIDENCE and _has_crystallized_habit_skill(local_context.habit_skills):
        return True
    return False


def _has_crystallized_habit_skill(habit_skills: list[dict[str, Any]]) -> bool:
    """Return whether the local context already has a strong crystallized habit skill."""

    return any(bool(skill.get("crystallized", False)) for skill in habit_skills if isinstance(skill, dict))


def _sanitize_llm_advisory_context(payload: WorkingMemoryAdapterResponse | dict[str, Any] | None) -> dict[str, Any]:
    """Keep only bounded advisory llm fields that cannot act as release authority."""

    if isinstance(payload, WorkingMemoryAdapterResponse):
        return payload.to_dict()
    if not isinstance(payload, dict):
        return {}
    advisory_context: dict[str, Any] = {}
    for field_name in ("candidate_suggestions", "prediction_hints", "reasoning_trace"):
        raw_values = payload.get(field_name)
        if isinstance(raw_values, list):
            advisory_context[field_name] = [value for value in raw_values if isinstance(value, str) and value]
    if "confidence" in payload:
        advisory_context["confidence"] = round(max(0.0, min(1.0, float(payload.get("confidence", 0.0)))), 3)
    return advisory_context
