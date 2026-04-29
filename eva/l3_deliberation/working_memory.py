"""Rule-based and replaceable working-memory adapters for the Phase C learning layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..kernel import StateStore
from .contracts import DeliberationInput, HabitBiasSummary, WorkingMemoryContext
from .skill_library import derive_habit_skills
from .working_memory_adapter import NullWorkingMemoryAdapter, WorkingMemoryAdapter, WorkingMemoryAdapterRequest, WorkingMemoryAdapterResponse

AUTO_WORKING_MEMORY_BACKEND = "auto"
MIN_AUTO_LLM_CONFIDENCE = 0.6


def build_situation_key(deliberation_input: DeliberationInput) -> str:
    """Build the compact recurring-situation key for one deliberation input."""

    return build_situation_key_from_values(
        top_drive=str(deliberation_input.drive_broadcast.get("top_drive") or "unknown"),
        life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
        pressure_reason=_pressure_reason_from_input(deliberation_input),
    )


def build_situation_key_from_values(*, top_drive: str, life_state: str, pressure_reason: str) -> str:
    """Build the compact recurring-situation key from normalized values."""

    return "|".join(
        (
            str(top_drive or "unknown"),
            str(life_state or "unknown"),
            str(pressure_reason or "none"),
        )
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

    del memory_stubs
    situation_key = build_situation_key(deliberation_input)
    matching_habit_bias = [
        dict(entry)
        for entry in (habit_bias_entries or [])
        if str(entry.get("situation_key") or "") == situation_key
    ]
    if matching_habit_bias:
        bias_summaries = _latest_habit_bias_summaries(
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
    recent_outcomes = _recent_learning_outcomes(learning_outcomes, situation_key=situation_key, limit=max_recent_outcomes)
    if not recent_outcomes:
        recent_outcomes = _recent_response_history(
            response_history or [],
            top_drive=str(deliberation_input.drive_broadcast.get("top_drive") or "unknown"),
            life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
            pressure_reason=_pressure_reason_from_input(deliberation_input),
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
) -> WorkingMemoryContext:
    """Build working-memory context directly from the runtime store."""

    learning_outcomes = store.read_learning_outcomes()
    habit_bias_entries = store.read_habit_bias()
    response_history = store.read_response_history()
    memory_stubs = store.read_cognitive_memory_stub()
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


def summarize_habit_bias(learning_outcomes: list[dict[str, Any]], *, situation_key: str) -> list[HabitBiasSummary]:
    """Summarize recurring outcomes into evidence-weighted habit-bias entries."""

    grouped: dict[str, dict[str, Any]] = {}
    for record in learning_outcomes:
        if _situation_key_from_learning_outcome(record) != situation_key:
            continue
        candidate_profile = str(record.get("candidate_profile") or "unknown")
        entry = grouped.setdefault(
            candidate_profile,
            {
                "recorded_at": str(record.get("recorded_at") or ""),
                "preferred_action": None,
                "avoid_action": None,
                "support_count": 0,
                "failure_count": 0,
                "habit_skill_hit_count": 0,
                "habit_narrowed_count": 0,
                "recent_negative_count": 0,
                "last_outcome_delta": 0.0,
                "timestamps": [],
            },
        )
        delta = float(record.get("outcome_delta", 0.0))
        action = record.get("selected_action")
        recorded_at = str(record.get("recorded_at") or entry["recorded_at"])
        entry["recorded_at"] = recorded_at
        entry["timestamps"].append(recorded_at)
        entry["last_outcome_delta"] = delta
        content = record.get("content") or {}
        if bool(content.get("habit_skill_match", False)):
            entry["habit_skill_hit_count"] += 1
        if bool(content.get("habit_narrowed", False)):
            entry["habit_narrowed_count"] += 1
        if delta > 0:
            entry["support_count"] += 1
            if action is not None:
                entry["preferred_action"] = str(action)
        elif delta < 0:
            entry["failure_count"] += 1
            entry["recent_negative_count"] += 1
            if action is not None:
                entry["avoid_action"] = str(action)
    summaries: list[HabitBiasSummary] = []
    for candidate_profile, entry in grouped.items():
        evidence_count = entry["support_count"] + entry["failure_count"]
        bias_strength = 0.0 if evidence_count == 0 else (entry["support_count"] - entry["failure_count"]) / evidence_count
        stability_score = _stability_score(
            evidence_count=evidence_count,
            support_count=int(entry["support_count"]),
            failure_count=int(entry["failure_count"]),
        )
        confidence = _confidence_score(
            evidence_count=evidence_count,
            stability_score=stability_score,
            recent_negative_count=int(entry["recent_negative_count"]),
            last_recorded_at=str(entry["recorded_at"]),
        )
        summaries.append(
            HabitBiasSummary(
                recorded_at=entry["recorded_at"],
                situation_key=situation_key,
                candidate_profile=candidate_profile,
                preferred_action=entry["preferred_action"],
                avoid_action=entry["avoid_action"],
                support_count=int(entry["support_count"]),
                failure_count=int(entry["failure_count"]),
                evidence_count=evidence_count,
                habit_skill_hit_count=int(entry["habit_skill_hit_count"]),
                habit_narrowed_count=int(entry["habit_narrowed_count"]),
                recent_negative_count=int(entry["recent_negative_count"]),
                last_outcome_delta=float(entry["last_outcome_delta"]),
                bias_strength=round(bias_strength, 3),
                stability_score=round(stability_score, 3),
                confidence=round(confidence, 3),
                habit_eligible=False,
                habit_eligibility_reasons=(),
            )
        )
    return sorted(
        summaries,
        key=lambda summary: (
            -summary.confidence,
            -summary.stability_score,
            -abs(summary.bias_strength),
            summary.candidate_profile,
        ),
    )


def _pressure_reason_from_input(deliberation_input: DeliberationInput) -> str:
    """Return the most relevant pressure reason from the compatibility context."""

    pressure_table = deliberation_input.compatibility_pressure_table or {}
    pressures = pressure_table.get("pressures")
    if isinstance(pressures, list):
        for pressure in pressures:
            if str(pressure.get("type") or "") == "integrity":
                reason = str((pressure.get("evidence") or {}).get("reason") or pressure.get("pressure_reason") or pressure.get("reason") or "")
                if reason:
                    return reason
        if pressures:
            first = pressures[0]
            reason = str((first.get("evidence") or {}).get("reason") or first.get("pressure_reason") or first.get("reason") or "")
            if reason:
                return reason
    return "none"


def _situation_key_from_learning_outcome(record: dict[str, Any]) -> str:
    """Return the normalized situation key recorded with one learning outcome."""

    content = record.get("content") or {}
    stored = content.get("situation_key")
    if stored:
        return str(stored)
    return build_situation_key_from_values(
        top_drive=str(content.get("top_drive") or "unknown"),
        life_state=str(content.get("life_state") or "unknown"),
        pressure_reason=str(record.get("pressure_reason") or content.get("pressure_reason") or "none"),
    )


def _recent_learning_outcomes(learning_outcomes: list[dict[str, Any]], *, situation_key: str, limit: int) -> list[dict[str, Any]]:
    """Return compact recent learning outcomes for one matching situation."""

    matching = [record for record in learning_outcomes if _situation_key_from_learning_outcome(record) == situation_key]
    recent = matching[-limit:]
    return [
        _recent_outcome_trace(record)
        for record in recent
    ]


def _recent_outcome_trace(record: dict[str, Any]) -> dict[str, Any]:
    """Return one compact recent outcome plus habitual trace labels."""

    content = record.get("content") or {}
    habit_skill_match = bool(content.get("habit_skill_match", False))
    habit_narrowed = bool(content.get("habit_narrowed", False))
    outcome_delta = float(record.get("outcome_delta", 0.0))
    evaluation_label = str(record.get("evaluation_label") or "unknown")
    trace_reasons: list[str] = []
    if habit_skill_match:
        trace_reasons.append("habit_skill_match")
    if habit_narrowed:
        trace_reasons.append("habit_narrowed")
    if outcome_delta < 0.0 or evaluation_label == "negative":
        trace_reasons.append("recent_negative_feedback")
    elif outcome_delta > 0.0 or evaluation_label == "positive":
        trace_reasons.append("recent_positive_feedback")
    habitual_trace = "habitual_support"
    if "recent_negative_feedback" in trace_reasons:
        habitual_trace = "habitual_suppression"
    elif not trace_reasons:
        habitual_trace = "habitual_neutral"
    return {
        "recorded_at": record.get("recorded_at"),
        "candidate_profile": record.get("candidate_profile"),
        "selected_action": record.get("selected_action"),
        "observed_outcome": record.get("observed_outcome"),
        "evaluation_label": evaluation_label,
        "outcome_delta": record.get("outcome_delta"),
        "confidence": record.get("confidence", 0.0),
        "habit_skill_match": habit_skill_match,
        "habit_narrowed": habit_narrowed,
        "habitual_trace": habitual_trace,
        "habitual_trace_reasons": trace_reasons,
    }


def _latest_habit_bias_summaries(
    habit_bias_entries: list[dict[str, Any]],
    *,
    max_bias_summaries: int,
) -> list[dict[str, Any]]:
    """Return the latest append-only habit-bias entry per candidate profile."""

    latest_by_profile: dict[str, dict[str, Any]] = {}
    for entry in habit_bias_entries:
        candidate_profile = str(entry.get("candidate_profile") or "unknown")
        latest_by_profile[candidate_profile] = dict(entry)
    latest = sorted(
        latest_by_profile.values(),
        key=lambda entry: (
            -float(entry.get("confidence", 0.0)),
            -float(entry.get("stability_score", 0.0)),
            -abs(float(entry.get("bias_strength", 0.0))),
            str(entry.get("candidate_profile") or "unknown"),
        ),
    )
    return latest[:max_bias_summaries]


def _recent_response_history(
    response_history: list[dict[str, Any]],
    *,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return compact recent response history entries when learning outcomes do not yet exist."""

    matching = []
    for entry in response_history:
        drive_context = entry.get("drive_context") or {}
        if str(drive_context.get("top_drive") or "unknown") != str(top_drive):
            continue
        if str(entry.get("life_state") or "unknown") != str(life_state):
            continue
        if str(entry.get("pressure_reason") or "none") != str(pressure_reason):
            continue
        matching.append(
            {
                "recorded_at": entry.get("recorded_at"),
                "selected_action": entry.get("selected_action"),
                "pressure_outcome": entry.get("pressure_outcome"),
                "execution_status": entry.get("execution_status"),
                "followup_needed": entry.get("followup_needed"),
            }
        )
    return matching[-limit:]



def _stability_score(*, evidence_count: int, support_count: int, failure_count: int) -> float:
    """Return how internally consistent the accumulated evidence is."""

    if evidence_count <= 0:
        return 0.0
    return min(1.0, abs(support_count - failure_count) / evidence_count)



def _confidence_score(
    *,
    evidence_count: int,
    stability_score: float,
    recent_negative_count: int,
    last_recorded_at: str,
) -> float:
    """Return a bounded confidence score for one habit-bias summary."""

    evidence_factor = min(1.0, evidence_count / 3.0)
    confidence = evidence_factor * stability_score
    if recent_negative_count > 1:
        confidence *= 0.75
    if _is_stale_record(last_recorded_at):
        confidence *= 0.5
    return max(0.0, min(1.0, confidence))



def _is_stale_record(recorded_at: str) -> bool:
    """Return whether a recorded-at timestamp is stale for C-2 bias reinforcement."""

    if not recorded_at:
        return True
    try:
        normalized = recorded_at.replace("Z", "+00:00")
        recorded = datetime.fromisoformat(normalized)
    except ValueError:
        return True
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    age_days = (now - recorded).total_seconds() / 86400.0
    return age_days > 30.0
