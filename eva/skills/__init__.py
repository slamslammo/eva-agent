"""Framework skill-source registries for Stage G capability landing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillProvenance:
    """Common provenance metadata carried by all skill-source records."""

    source: str
    provenance_detail: str
    confidence: float
    scope: dict[str, Any] = field(default_factory=dict)
    mutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "provenance_detail": self.provenance_detail,
            "confidence": self.confidence,
            "scope": dict(self.scope),
            "mutable": self.mutable,
        }


@dataclass(frozen=True)
class PriorSkillRecord:
    """Framework-owned designer/scenario-given prior skill record."""

    recorded_at: str
    situation_key: str
    candidate_profile: str
    preferred_action: str | None = None
    avoid_action: str | None = None
    provenance: SkillProvenance = field(default_factory=lambda: SkillProvenance(source="scenario", provenance_detail="", confidence=0.0))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "candidate_profile": self.candidate_profile,
            "provenance": self.provenance.to_dict(),
        }
        if self.preferred_action is not None:
            payload["preferred_action"] = self.preferred_action
        if self.avoid_action is not None:
            payload["avoid_action"] = self.avoid_action
        return payload


@dataclass(frozen=True)
class HabitSkillRecord:
    """Framework-owned experience-derived habit skill record."""

    recorded_at: str
    situation_key: str
    candidate_profile: str
    preferred_action: str | None = None
    evidence_count: int = 0
    stability_score: float = 0.0
    confidence: float = 0.0
    crystallized: bool = False
    crystallization_reasons: tuple[str, ...] = ()
    provenance: SkillProvenance = field(default_factory=lambda: SkillProvenance(source="experience", provenance_detail="", confidence=0.0))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "candidate_profile": self.candidate_profile,
            "evidence_count": self.evidence_count,
            "stability_score": self.stability_score,
            "confidence": self.confidence,
            "crystallized": self.crystallized,
            "crystallization_reasons": list(self.crystallization_reasons),
            "provenance": self.provenance.to_dict(),
        }
        if self.preferred_action is not None:
            payload["preferred_action"] = self.preferred_action
        return payload


class PriorSkillRegistry:
    """Minimal framework registry for prior skill records."""

    def __init__(self, records: list[PriorSkillRecord] | None = None) -> None:
        self._records = list(records or [])

    def records(self) -> list[PriorSkillRecord]:
        return list(self._records)

    def for_situation(self, situation_key: str) -> list[PriorSkillRecord]:
        return [record for record in self._records if record.situation_key == situation_key]


class HabitSkillRegistry:
    """Minimal framework registry for habit skill records."""

    def __init__(self, records: list[HabitSkillRecord] | None = None) -> None:
        self._records = list(records or [])

    def records(self) -> list[HabitSkillRecord]:
        return list(self._records)

    def for_situation(self, situation_key: str) -> list[HabitSkillRecord]:
        return [record for record in self._records if record.situation_key == situation_key]


class InheritedPriorRegistry:
    """Placeholder registry reserved for v0.7+ inherited priors."""

    def records(self) -> list[dict[str, Any]]:
        return []

    def for_situation(self, situation_key: str) -> list[dict[str, Any]]:
        del situation_key
        return []

    def register(self, record: dict[str, Any]) -> None:
        del record
        raise NotImplementedError("InheritedPriorRegistry is reserved for v0.7+")


__all__ = [
    "HabitSkillRecord",
    "HabitSkillRegistry",
    "InheritedPriorRegistry",
    "PriorSkillRecord",
    "PriorSkillRegistry",
    "SkillProvenance",
]
