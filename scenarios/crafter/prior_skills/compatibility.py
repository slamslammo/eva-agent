"""Crafter prior-skill derivation and registry policy for Stage H H-4."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from eva.kernel.state import from_iso8601
from eva.skills import PriorSkillRecord, PriorSkillRegistry, SkillProvenance

MIN_SKILL_EVIDENCE = 3
MIN_SKILL_STABILITY = 0.6
MIN_SKILL_CONFIDENCE = 0.6
MIN_SKILL_HIT_COUNT = 3
MIN_SKILL_EFFECTIVE_HITS = 4
MAX_SKILL_RECENT_NEGATIVE = 1
MIN_SKILL_LAST_OUTCOME_DELTA = 0.0
PRIOR_SKILL_MATCH_PROFILES = frozenset({"observe_first", "stabilize_first", "escalate_first"})


def habit_skill_match_for_candidate_profile(candidate_profile: str | None) -> bool:
    return str(candidate_profile or "") in PRIOR_SKILL_MATCH_PROFILES


def build_situation_key_from_values(*, top_drive: str, life_state: str, pressure_reason: str) -> str:
    return "|".join((str(top_drive or "unknown"), str(life_state or "unknown"), str(pressure_reason or "none")))


def derive_habit_skills(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]] | None = None,
    learning_outcomes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    bias_entries = _source_habit_bias_entries(
        situation_key=situation_key,
        habit_bias_entries=habit_bias_entries or [],
        learning_outcomes=learning_outcomes or [],
    )
    skills: list[dict[str, Any]] = []
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
        skills.append(
            {
                "recorded_at": str(entry.get("recorded_at") or ""),
                "situation_key": situation_key,
                "candidate_profile": str(entry.get("candidate_profile") or "unknown"),
                "preferred_action": str(entry.get("preferred_action")) if entry.get("preferred_action") is not None else None,
                "evidence_count": evidence_count,
                "stability_score": stability_score,
                "confidence": confidence,
                "crystallized": not crystallization_reasons,
                "crystallization_reasons": list(crystallization_reasons),
                "source": "habit_bias",
            }
        )
    return sorted(
        skills,
        key=lambda skill: (
            not bool(skill.get("crystallized", False)),
            -float(skill.get("confidence", 0.0)),
            -float(skill.get("stability_score", 0.0)),
            -int(skill.get("evidence_count", 0)),
            str(skill.get("candidate_profile") or "unknown"),
        ),
    )


def summarize_habit_bias(learning_outcomes: list[dict[str, Any]], *, situation_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in learning_outcomes:
        if situation_key_from_learning_outcome(record) != situation_key:
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
        entry["recorded_at"] = str(record.get("recorded_at") or entry["recorded_at"])
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
    summaries: list[dict[str, Any]] = []
    for candidate_profile, entry in grouped.items():
        evidence_count = int(entry["support_count"]) + int(entry["failure_count"])
        bias_strength = 0.0 if evidence_count == 0 else (int(entry["support_count"]) - int(entry["failure_count"])) / evidence_count
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
            {
                "recorded_at": str(entry["recorded_at"]),
                "situation_key": situation_key,
                "candidate_profile": candidate_profile,
                "preferred_action": entry["preferred_action"],
                "avoid_action": entry["avoid_action"],
                "support_count": int(entry["support_count"]),
                "failure_count": int(entry["failure_count"]),
                "evidence_count": evidence_count,
                "habit_skill_hit_count": int(entry["habit_skill_hit_count"]),
                "habit_narrowed_count": int(entry["habit_narrowed_count"]),
                "recent_negative_count": int(entry["recent_negative_count"]),
                "last_outcome_delta": float(entry["last_outcome_delta"]),
                "bias_strength": round(bias_strength, 3),
                "stability_score": round(stability_score, 3),
                "confidence": round(confidence, 3),
                "habit_eligible": False,
                "habit_eligibility_reasons": [],
            }
        )
    return sorted(
        summaries,
        key=lambda summary: (
            -float(summary.get("confidence", 0.0)),
            -float(summary.get("stability_score", 0.0)),
            -abs(float(summary.get("bias_strength", 0.0))),
            str(summary.get("candidate_profile") or "unknown"),
        ),
    )


def situation_key_from_learning_outcome(record: dict[str, Any]) -> str:
    content = record.get("content") or {}
    stored = content.get("situation_key")
    if stored:
        return str(stored)
    return build_situation_key_from_values(
        top_drive=str(content.get("top_drive") or "unknown"),
        life_state=str(content.get("life_state") or "unknown"),
        pressure_reason=str(record.get("pressure_reason") or content.get("pressure_reason") or "none"),
    )


def prior_skill_registry(*, top_drive: str, life_state: str, pressure_reason: str) -> PriorSkillRegistry:
    situation_key = build_situation_key_from_values(
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
    )
    records = [
        _prior_record(
            situation_key=situation_key,
            candidate_profile=profile,
            preferred_action=preferred_action,
            provenance_detail=provenance_detail,
            confidence=confidence,
            mutable=mutable,
            top_drive=top_drive,
            pressure_reason=pressure_reason,
        )
        for profile, preferred_action, provenance_detail, confidence, mutable in _prior_profiles_for_context(
            top_drive=top_drive,
            pressure_reason=pressure_reason,
        )
    ]
    return PriorSkillRegistry(records)


def _prior_profiles_for_context(*, top_drive: str, pressure_reason: str) -> list[tuple[str, str | None, str, float, bool]]:
    if pressure_reason in {"health_critical", "threat_visible"} or top_drive == "safety":
        return [
            ("escalate_first", "do", "crafter_runtime_survival_prior", 0.9, True),
            ("stabilize_first", "sleep", "crafter_runtime_survival_prior", 0.75, True),
        ]
    if pressure_reason in {"water_critical", "food_critical", "energy_critical"} or top_drive in {"metabolic", "recovery"}:
        preferred = "sleep" if pressure_reason == "energy_critical" or top_drive == "recovery" else "do"
        return [
            ("stabilize_first", preferred, "crafter_runtime_survival_prior", 0.85, True),
            ("observe_first", "noop", "crafter_runtime_recognition_prior", 0.6, True),
        ]
    if top_drive in {"acquisition", "capability"}:
        return [
            ("observe_first", "noop", "crafter_runtime_resource_chain_prior", 0.8, True),
            ("stabilize_first", "sleep", "crafter_runtime_survival_prior", 0.5, True),
        ]
    return [("observe_first", "noop", "crafter_runtime_action_semantics", 0.7, False)]


def _prior_record(
    *,
    situation_key: str,
    candidate_profile: str,
    preferred_action: str | None,
    provenance_detail: str,
    confidence: float,
    mutable: bool,
    top_drive: str,
    pressure_reason: str,
) -> PriorSkillRecord:
    return PriorSkillRecord(
        recorded_at="scenario_definition",
        situation_key=situation_key,
        candidate_profile=candidate_profile,
        preferred_action=preferred_action,
        provenance=SkillProvenance(
            source="scenario",
            provenance_detail=provenance_detail,
            confidence=confidence,
            scope={"scenario": "crafter", "top_drive": top_drive, "pressure_reason": pressure_reason},
            mutable=mutable,
        ),
    )


def _source_habit_bias_entries(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]],
    learning_outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matching_entries = [dict(entry) for entry in habit_bias_entries if str(entry.get("situation_key") or "") == situation_key]
    if matching_entries:
        latest_by_profile: dict[str, dict[str, Any]] = {}
        for entry in matching_entries:
            latest_by_profile[str(entry.get("candidate_profile") or "unknown")] = dict(entry)
        return list(latest_by_profile.values())
    return summarize_habit_bias(learning_outcomes, situation_key=situation_key)


def _stability_score(*, evidence_count: int, support_count: int, failure_count: int) -> float:
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
    evidence_factor = min(1.0, evidence_count / 3.0)
    confidence = evidence_factor * stability_score
    if recent_negative_count > 1:
        confidence *= 0.75
    if _is_stale_record(last_recorded_at):
        confidence *= 0.5
    return max(0.0, min(1.0, confidence))


def _is_stale_record(recorded_at: str) -> bool:
    recorded = from_iso8601(recorded_at)
    if recorded is None:
        return True
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return ((now - recorded).total_seconds() / 86400.0) > 30.0


__all__ = [
    "PRIOR_SKILL_MATCH_PROFILES",
    "build_situation_key_from_values",
    "derive_habit_skills",
    "habit_skill_match_for_candidate_profile",
    "prior_skill_registry",
    "situation_key_from_learning_outcome",
    "summarize_habit_bias",
]
