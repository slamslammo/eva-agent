"""Minimal Phase C-3 habit-skill derivation built on top of habit bias summaries."""

from __future__ import annotations

from typing import Any

from .contracts import HabitSkillSummary


MIN_SKILL_EVIDENCE = 3
MIN_SKILL_STABILITY = 0.6
MIN_SKILL_CONFIDENCE = 0.6
MIN_SKILL_HIT_COUNT = 3
MIN_SKILL_EFFECTIVE_HITS = 4
MAX_SKILL_RECENT_NEGATIVE = 1
MIN_SKILL_LAST_OUTCOME_DELTA = 0.0


def derive_habit_skills(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]] | None = None,
    learning_outcomes: list[dict[str, Any]] | None = None,
) -> list[HabitSkillSummary]:
    """Derive crystallized habit-skill summaries from current learning artifacts."""

    bias_entries = _source_habit_bias_entries(
        situation_key=situation_key,
        habit_bias_entries=habit_bias_entries or [],
        learning_outcomes=learning_outcomes or [],
    )
    skills: list[HabitSkillSummary] = []
    for entry in bias_entries:
        evidence_count = int(entry.get("evidence_count", 0))
        stability_score = float(entry.get("stability_score", 0.0))
        confidence = float(entry.get("confidence", 0.0))
        habit_skill_hit_count = int(entry.get("habit_skill_hit_count", evidence_count))
        habit_narrowed_count = int(entry.get("habit_narrowed_count", 0))
        recent_negative_count = int(entry.get("recent_negative_count", 0))
        last_outcome_delta = float(entry.get("last_outcome_delta", 0.0))
        effective_hit_count = habit_skill_hit_count + habit_narrowed_count
        crystallization_reasons: list[str] = []
        if evidence_count < MIN_SKILL_EVIDENCE:
            crystallization_reasons.append("insufficient_evidence")
        if stability_score < MIN_SKILL_STABILITY:
            crystallization_reasons.append("insufficient_stability")
        if confidence < MIN_SKILL_CONFIDENCE:
            crystallization_reasons.append("insufficient_confidence")
        if habit_skill_hit_count < MIN_SKILL_HIT_COUNT:
            crystallization_reasons.append("insufficient_habit_hits")
        if effective_hit_count < MIN_SKILL_EFFECTIVE_HITS:
            crystallization_reasons.append("insufficient_effective_hits")
        if recent_negative_count > MAX_SKILL_RECENT_NEGATIVE:
            crystallization_reasons.append("recent_negative_streak")
        if last_outcome_delta < MIN_SKILL_LAST_OUTCOME_DELTA:
            crystallization_reasons.append("last_outcome_negative")
        crystallized = not crystallization_reasons
        skills.append(
            HabitSkillSummary(
                recorded_at=str(entry.get("recorded_at") or ""),
                situation_key=situation_key,
                candidate_profile=str(entry.get("candidate_profile") or "unknown"),
                preferred_action=(str(entry.get("preferred_action")) if entry.get("preferred_action") is not None else None),
                evidence_count=evidence_count,
                stability_score=stability_score,
                confidence=confidence,
                crystallized=crystallized,
                crystallization_reasons=tuple(crystallization_reasons),
                source="habit_bias",
            )
        )
    return sorted(
        skills,
        key=lambda skill: (
            not skill.crystallized,
            -skill.confidence,
            -skill.stability_score,
            -skill.evidence_count,
            skill.candidate_profile,
        ),
    )


def _source_habit_bias_entries(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]],
    learning_outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return current habit-bias entries or derive them from learning outcomes."""

    matching_entries = [
        dict(entry)
        for entry in habit_bias_entries
        if str(entry.get("situation_key") or "") == situation_key
    ]
    if matching_entries:
        latest_by_profile: dict[str, dict[str, Any]] = {}
        for entry in matching_entries:
            latest_by_profile[str(entry.get("candidate_profile") or "unknown")] = dict(entry)
        return list(latest_by_profile.values())
    return _summaries_from_learning_outcomes(learning_outcomes, situation_key=situation_key)



def _summaries_from_learning_outcomes(
    learning_outcomes: list[dict[str, Any]],
    *,
    situation_key: str,
) -> list[dict[str, Any]]:
    """Derive minimal habit-bias-like summaries without importing working_memory."""

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
                "support_count": 0,
                "failure_count": 0,
                "habit_skill_hit_count": 0,
                "habit_narrowed_count": 0,
            },
        )
        delta = float(record.get("outcome_delta", 0.0))
        entry["recorded_at"] = str(record.get("recorded_at") or entry["recorded_at"])
        content = record.get("content") or {}
        if bool(content.get("habit_skill_match", False)):
            entry["habit_skill_hit_count"] += 1
        if bool(content.get("habit_narrowed", False)):
            entry["habit_narrowed_count"] += 1
        if delta > 0:
            entry["support_count"] += 1
            if record.get("selected_action") is not None:
                entry["preferred_action"] = str(record.get("selected_action"))
        elif delta < 0:
            entry["failure_count"] += 1
    summaries: list[dict[str, Any]] = []
    for candidate_profile, entry in grouped.items():
        evidence_count = int(entry["support_count"]) + int(entry["failure_count"])
        stability_score = 0.0
        if evidence_count > 0:
            stability_score = min(1.0, abs(int(entry["support_count"]) - int(entry["failure_count"])) / evidence_count)
        confidence = min(1.0, min(1.0, evidence_count / 3.0) * stability_score)
        summaries.append(
            {
                "recorded_at": entry["recorded_at"],
                "situation_key": situation_key,
                "candidate_profile": candidate_profile,
                "preferred_action": entry["preferred_action"],
                "evidence_count": evidence_count,
                "habit_skill_hit_count": int(entry["habit_skill_hit_count"]),
                "habit_narrowed_count": int(entry["habit_narrowed_count"]),
                "stability_score": round(stability_score, 3),
                "confidence": round(confidence, 3),
            }
        )
    return summaries



def _situation_key_from_learning_outcome(record: dict[str, Any]) -> str:
    """Return the normalized situation key recorded with one learning outcome."""

    content = record.get("content") or {}
    stored = content.get("situation_key")
    if stored:
        return str(stored)
    return "|".join(
        (
            str(content.get("top_drive") or "unknown"),
            str(content.get("life_state") or "unknown"),
            str(record.get("pressure_reason") or content.get("pressure_reason") or "none"),
        )
    )
