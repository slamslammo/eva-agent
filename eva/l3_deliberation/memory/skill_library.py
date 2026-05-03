"""Minimal Phase C-3 habit-skill derivation built on top of habit bias summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

MIN_SKILL_EVIDENCE = 3
MIN_SKILL_STABILITY = 0.6
MIN_SKILL_CONFIDENCE = 0.6
MIN_SKILL_HIT_COUNT = 3
MIN_SKILL_EFFECTIVE_HITS = 4
MAX_SKILL_RECENT_NEGATIVE = 1
MIN_SKILL_LAST_OUTCOME_DELTA = 0.0


@dataclass(frozen=True)
class HabitSkillSummary:
    """Phase C-3 crystallized habit skill summary for one recurring situation."""

    recorded_at: str
    situation_key: str
    candidate_profile: str
    preferred_action: str | None = None
    evidence_count: int = 0
    stability_score: float = 0.0
    confidence: float = 0.0
    crystallized: bool = False
    crystallization_reasons: tuple[str, ...] = ()
    source: str = "habit_bias"

    def to_dict(self) -> dict[str, Any]:
        """Serialize one habit-skill summary."""

        payload = {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "candidate_profile": self.candidate_profile,
            "evidence_count": self.evidence_count,
            "stability_score": self.stability_score,
            "confidence": self.confidence,
            "crystallized": self.crystallized,
            "crystallization_reasons": list(self.crystallization_reasons),
            "source": self.source,
        }
        if self.preferred_action is not None:
            payload["preferred_action"] = self.preferred_action
        return payload


@dataclass(frozen=True)
class HabitBiasSummary:
    """Phase C habit-bias summary for one recurring situation."""

    recorded_at: str
    situation_key: str
    candidate_profile: str
    preferred_action: str | None = None
    avoid_action: str | None = None
    support_count: int = 0
    failure_count: int = 0
    evidence_count: int = 0
    habit_skill_hit_count: int = 0
    habit_narrowed_count: int = 0
    recent_negative_count: int = 0
    last_outcome_delta: float = 0.0
    bias_strength: float = 0.0
    stability_score: float = 0.0
    confidence: float = 0.0
    habit_eligible: bool = False
    habit_eligibility_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize one habit-bias summary."""

        payload = {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "candidate_profile": self.candidate_profile,
            "support_count": self.support_count,
            "failure_count": self.failure_count,
            "evidence_count": self.evidence_count,
            "habit_skill_hit_count": self.habit_skill_hit_count,
            "habit_narrowed_count": self.habit_narrowed_count,
            "recent_negative_count": self.recent_negative_count,
            "last_outcome_delta": self.last_outcome_delta,
            "bias_strength": self.bias_strength,
            "stability_score": self.stability_score,
            "confidence": self.confidence,
            "habit_eligible": self.habit_eligible,
            "habit_eligibility_reasons": list(self.habit_eligibility_reasons),
        }
        if self.preferred_action is not None:
            payload["preferred_action"] = self.preferred_action
        if self.avoid_action is not None:
            payload["avoid_action"] = self.avoid_action
        return payload


def build_situation_key_from_values(*, top_drive: str, life_state: str, pressure_reason: str) -> str:
    """Build the compact recurring-situation key from normalized values."""

    return "|".join(
        (
            str(top_drive or "unknown"),
            str(life_state or "unknown"),
            str(pressure_reason or "none"),
        )
    )


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
    """Derive minimal habit-bias-like summaries from learning outcomes."""

    return [summary.to_dict() for summary in summarize_habit_bias(learning_outcomes, situation_key=situation_key)]



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
            },
        )
        delta = float(record.get("outcome_delta", 0.0))
        action = record.get("selected_action")
        recorded_at = str(record.get("recorded_at") or entry["recorded_at"])
        entry["recorded_at"] = recorded_at
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
