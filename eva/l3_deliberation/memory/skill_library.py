"""Framework prior-skill compatibility seam for Phase A."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...scenario_bundle import get_active_runtime_scenario
from ...skills import (
    HabitSkillRecord,
    HabitSkillRegistry,
    InheritedPriorRecord,
    InheritedPriorRegistry,
    PriorSkillRecord,
    PriorSkillRegistry,
    SkillProvenance,
)


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
    provenance: dict[str, Any] | None = None

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
        if self.provenance is not None:
            payload["provenance"] = dict(self.provenance)
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

    return get_active_runtime_scenario().prior_skills.build_situation_key_from_values(
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
    )


def derive_habit_skills(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]] | None = None,
    learning_outcomes: list[dict[str, Any]] | None = None,
) -> list[HabitSkillSummary]:
    """Derive crystallized habit-skill summaries from current learning artifacts."""

    habit_records = habit_skill_registry(
        situation_key=situation_key,
        habit_bias_entries=habit_bias_entries,
        learning_outcomes=learning_outcomes,
    ).records()
    return [
        HabitSkillSummary(
            recorded_at=record.recorded_at,
            situation_key=record.situation_key,
            candidate_profile=record.candidate_profile,
            preferred_action=record.preferred_action,
            evidence_count=record.evidence_count,
            stability_score=record.stability_score,
            confidence=record.confidence,
            crystallized=record.crystallized,
            crystallization_reasons=record.crystallization_reasons,
            source="habit_bias",
            provenance=record.provenance.to_dict(),
        )
        for record in habit_records
    ]


def _situation_key_from_learning_outcome(record: dict[str, Any]) -> str:
    """Return the normalized situation key recorded with one learning outcome."""

    return get_active_runtime_scenario().prior_skills.situation_key_from_learning_outcome(record)


def summarize_habit_bias(learning_outcomes: list[dict[str, Any]], *, situation_key: str) -> list[HabitBiasSummary]:
    """Summarize recurring outcomes into evidence-weighted habit-bias entries."""

    summaries = get_active_runtime_scenario().prior_skills.summarize_habit_bias(
        learning_outcomes,
        situation_key=situation_key,
    )
    return [
        HabitBiasSummary(
            recorded_at=str(summary.get("recorded_at") or ""),
            situation_key=str(summary.get("situation_key") or situation_key),
            candidate_profile=str(summary.get("candidate_profile") or "unknown"),
            preferred_action=(str(summary.get("preferred_action")) if summary.get("preferred_action") is not None else None),
            avoid_action=(str(summary.get("avoid_action")) if summary.get("avoid_action") is not None else None),
            support_count=int(summary.get("support_count", 0)),
            failure_count=int(summary.get("failure_count", 0)),
            evidence_count=int(summary.get("evidence_count", 0)),
            habit_skill_hit_count=int(summary.get("habit_skill_hit_count", 0)),
            habit_narrowed_count=int(summary.get("habit_narrowed_count", 0)),
            recent_negative_count=int(summary.get("recent_negative_count", 0)),
            last_outcome_delta=float(summary.get("last_outcome_delta", 0.0)),
            bias_strength=float(summary.get("bias_strength", 0.0)),
            stability_score=float(summary.get("stability_score", 0.0)),
            confidence=float(summary.get("confidence", 0.0)),
            habit_eligible=bool(summary.get("habit_eligible", False)),
            habit_eligibility_reasons=tuple(str(reason) for reason in summary.get("habit_eligibility_reasons", [])),
        )
        for summary in summaries
    ]


def habit_skill_registry(
    *,
    situation_key: str,
    habit_bias_entries: list[dict[str, Any]] | None = None,
    learning_outcomes: list[dict[str, Any]] | None = None,
) -> HabitSkillRegistry:
    """Return the current scenario habit-skill registry for one situation."""

    skills = get_active_runtime_scenario().prior_skills.derive_habit_skills(
        situation_key=situation_key,
        habit_bias_entries=habit_bias_entries,
        learning_outcomes=learning_outcomes,
    )
    scenario_name = get_active_runtime_scenario().name
    records = [
        HabitSkillRecord(
            recorded_at=str(skill.get("recorded_at") or ""),
            situation_key=str(skill.get("situation_key") or situation_key),
            candidate_profile=str(skill.get("candidate_profile") or "unknown"),
            preferred_action=(str(skill.get("preferred_action")) if skill.get("preferred_action") is not None else None),
            evidence_count=int(skill.get("evidence_count", 0)),
            stability_score=float(skill.get("stability_score", 0.0)),
            confidence=float(skill.get("confidence", 0.0)),
            crystallized=bool(skill.get("crystallized", False)),
            crystallization_reasons=tuple(str(reason) for reason in skill.get("crystallization_reasons", [])),
            provenance=SkillProvenance(
                source="experience",
                provenance_detail=f"{scenario_name}_procedural_memory_derivation",
                confidence=float(skill.get("confidence", 0.0)),
                scope={"scenario": scenario_name, "situation_key": situation_key},
                mutable=True,
            ),
        )
        for skill in skills
    ]
    return HabitSkillRegistry(records)


def _parse_situation_key(situation_key: str) -> tuple[str, str, str]:
    parts = str(situation_key or "").split("|", 2)
    if len(parts) == 3:
        return parts[0] or "unknown", parts[1] or "unknown", parts[2] or "none"
    return str(situation_key or "unknown"), "unknown", "none"


def prior_skill_registry(*, situation_key: str) -> PriorSkillRegistry:
    """Return the current scenario prior-skill registry for one situation."""

    top_drive, life_state, pressure_reason = _parse_situation_key(situation_key)
    return get_active_runtime_scenario().prior_skills.build_prior_skill_registry(
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
        situation_key=situation_key,
    )


def inherited_prior_registry(*, path: str | None = None) -> InheritedPriorRegistry:
    """Return the current scenario inherited-prior registry for optional cross-life reuse."""

    return get_active_runtime_scenario().prior_skills.build_inherited_prior_registry(path)


__all__ = [
    "HabitBiasSummary",
    "HabitSkillSummary",
    "build_situation_key_from_values",
    "derive_habit_skills",
    "habit_skill_registry",
    "inherited_prior_registry",
    "prior_skill_registry",
    "summarize_habit_bias",
]
