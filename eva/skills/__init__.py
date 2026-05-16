"""Framework skill-source registries for Stage G capability landing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
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
class EpisodicMemoryRecord:
    """Framework-owned episodic memory record with situational anchoring."""

    recorded_at: str
    situation_key: str
    memory_type: str
    content: dict[str, Any] = field(default_factory=dict)
    provenance: SkillProvenance = field(default_factory=lambda: SkillProvenance(source="experience", provenance_detail="", confidence=0.0))
    salience: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "memory_type": self.memory_type,
            "content": dict(self.content),
            "provenance": self.provenance.to_dict(),
            "salience": self.salience,
        }


@dataclass(frozen=True)
class SemanticMemoryRecord:
    """Framework-owned semantic memory record extracted from episodes."""

    recorded_at: str
    pattern_summary: str
    extracted_from_episodes: tuple[str, ...] = ()
    confidence: float = 0.0
    scope: dict[str, Any] = field(default_factory=dict)
    provenance: SkillProvenance = field(default_factory=lambda: SkillProvenance(source="experience", provenance_detail="", confidence=0.0))
    preferred_candidate_profiles: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_at": self.recorded_at,
            "pattern_summary": self.pattern_summary,
            "extracted_from_episodes": list(self.extracted_from_episodes),
            "confidence": self.confidence,
            "scope": dict(self.scope),
            "provenance": self.provenance.to_dict(),
            "preferred_candidate_profiles": list(self.preferred_candidate_profiles),
        }


@dataclass(frozen=True)
class ProceduralMemoryRecord:
    """Framework-owned procedural memory record for condition-matched action patterns."""

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


class EpisodicMemoryRegistry:
    """Minimal framework registry for episodic memory records."""

    def __init__(self, records: list[EpisodicMemoryRecord] | None = None) -> None:
        self._records = list(records or [])

    def records(self) -> list[EpisodicMemoryRecord]:
        return list(self._records)

    def for_situation(self, situation_key: str) -> list[EpisodicMemoryRecord]:
        return [record for record in self._records if record.situation_key == situation_key]


class SemanticMemoryRegistry:
    """Minimal framework registry for semantic memory records."""

    def __init__(self, records: list[SemanticMemoryRecord] | None = None) -> None:
        self._records = list(records or [])

    def records(self) -> list[SemanticMemoryRecord]:
        return list(self._records)

    def for_topic(self, topic: str) -> list[SemanticMemoryRecord]:
        return [record for record in self._records if str(record.scope.get("topic") or "") == topic]

    def for_scope(self, **scope_filters: Any) -> list[SemanticMemoryRecord]:
        return [
            record
            for record in self._records
            if all(record.scope.get(key) == value for key, value in scope_filters.items())
        ]


class ProceduralMemoryRegistry:
    """Minimal framework registry for procedural memory records."""

    def __init__(self, records: list[ProceduralMemoryRecord] | None = None) -> None:
        self._records = list(records or [])

    def records(self) -> list[ProceduralMemoryRecord]:
        return list(self._records)

    def for_situation(self, situation_key: str) -> list[ProceduralMemoryRecord]:
        return [record for record in self._records if record.situation_key == situation_key]


HabitSkillRecord = ProceduralMemoryRecord


class HabitSkillRegistry(ProceduralMemoryRegistry):
    """Backward-compatible alias for the Stage I procedural memory registry."""


@dataclass(frozen=True)
class InheritedPriorRecord:
    """Framework-owned inherited prior record loaded from distilled bundles."""

    recorded_at: str
    situation_key: str
    candidate_profile: str
    preferred_action: str | None = None
    avoid_action: str | None = None
    evidence_count: int = 0
    stability_score: float = 0.0
    confidence: float = 0.0
    bias_strength: float = 0.0
    provenance: SkillProvenance = field(default_factory=lambda: SkillProvenance(source="inherited", provenance_detail="", confidence=0.0))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "recorded_at": self.recorded_at,
            "situation_key": self.situation_key,
            "candidate_profile": self.candidate_profile,
            "evidence_count": self.evidence_count,
            "stability_score": self.stability_score,
            "confidence": self.confidence,
            "bias_strength": self.bias_strength,
            "provenance": self.provenance.to_dict(),
        }
        if self.preferred_action is not None:
            payload["preferred_action"] = self.preferred_action
        if self.avoid_action is not None:
            payload["avoid_action"] = self.avoid_action
        return payload


class InheritedPriorRegistry:
    """Minimal framework registry for inherited prior records."""

    def __init__(self, records: list[InheritedPriorRecord] | None = None) -> None:
        self._records = list(records or [])
        self._records_by_situation: dict[str, list[InheritedPriorRecord]] = {}
        for record in self._records:
            self._records_by_situation.setdefault(record.situation_key, []).append(record)

    def records(self) -> list[InheritedPriorRecord]:
        return list(self._records)

    def for_situation(self, situation_key: str) -> list[InheritedPriorRecord]:
        return list(self._records_by_situation.get(situation_key, ()))

    def register(self, record: InheritedPriorRecord) -> None:
        self._records.append(record)
        self._records_by_situation.setdefault(record.situation_key, []).append(record)


def load_inherited_prior_registry(
    *,
    bundle_path: str | Path | None,
    expected_scenario: str,
    allowed_action_hints: frozenset[str],
    allowed_candidate_profiles: frozenset[str],
    default_provenance_detail: str,
) -> InheritedPriorRegistry:
    """Load one scenario-qualified inherited-prior bundle into a framework registry."""

    if bundle_path is None:
        return InheritedPriorRegistry()
    path = Path(bundle_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("inherited prior bundle must be a JSON object")
    if str(payload.get("scenario") or "") != expected_scenario:
        raise ValueError(f"inherited prior bundle scenario must be {expected_scenario}")
    recorded_at = str(payload.get("distillation_date") or payload.get("generated_at") or "distilled_bundle")
    records = [
        record
        for raw_record in payload.get("records", [])
        if isinstance(raw_record, dict)
        for record in [
            _inherited_prior_record_from_bundle(
                raw_record,
                recorded_at=recorded_at,
                expected_scenario=expected_scenario,
                allowed_action_hints=allowed_action_hints,
                allowed_candidate_profiles=allowed_candidate_profiles,
                default_provenance_detail=default_provenance_detail,
            )
        ]
        if record is not None
    ]
    return InheritedPriorRegistry(records)



def _inherited_prior_record_from_bundle(
    raw_record: dict[str, Any],
    *,
    recorded_at: str,
    expected_scenario: str,
    allowed_action_hints: frozenset[str],
    allowed_candidate_profiles: frozenset[str],
    default_provenance_detail: str,
) -> InheritedPriorRecord | None:
    scope = raw_record.get("scope") if isinstance(raw_record.get("scope"), dict) else {}
    content = raw_record.get("content") if isinstance(raw_record.get("content"), dict) else {}
    situation_key = str(content.get("situation_key") or scope.get("situation_key") or "")
    candidate_profile = str(content.get("candidate_profile") or "")
    if not situation_key or candidate_profile not in allowed_candidate_profiles:
        return None
    preferred_action = _optional_inherited_action_hint(content.get("preferred_action"), allowed_action_hints)
    avoid_action = _optional_inherited_action_hint(content.get("avoid_action"), allowed_action_hints)
    confidence = _bounded_probability(raw_record.get("confidence", content.get("confidence", 0.0)))
    stability_score = _bounded_probability(content.get("stability_score", 0.0))
    bias_strength = _bounded_bias_strength(content.get("bias_strength", 0.0))
    evidence_count = max(0, int(content.get("evidence_count", 0) or 0))
    return InheritedPriorRecord(
        recorded_at=recorded_at,
        situation_key=situation_key,
        candidate_profile=candidate_profile,
        preferred_action=preferred_action,
        avoid_action=avoid_action,
        evidence_count=evidence_count,
        stability_score=stability_score,
        confidence=confidence,
        bias_strength=bias_strength,
        provenance=SkillProvenance(
            source=str(raw_record.get("source") or "inherited"),
            provenance_detail=str(raw_record.get("provenance_detail") or default_provenance_detail),
            confidence=confidence,
            scope={
                "scenario": expected_scenario,
                "situation_key": situation_key,
                **{key: value for key, value in scope.items() if key != "scenario"},
            },
            mutable=bool(raw_record.get("mutable", True)),
        ),
    )



def _optional_inherited_action_hint(value: Any, allowed_action_hints: frozenset[str]) -> str | None:
    if value is None:
        return None
    normalized = str(value or "")
    if not normalized or normalized not in allowed_action_hints:
        return None
    return normalized



def _bounded_probability(value: Any) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)



def _bounded_bias_strength(value: Any) -> float:
    return round(max(-1.0, min(1.0, float(value))), 3)


__all__ = [
    "EpisodicMemoryRecord",
    "EpisodicMemoryRegistry",
    "HabitSkillRecord",
    "HabitSkillRegistry",
    "InheritedPriorRecord",
    "InheritedPriorRegistry",
    "PriorSkillRecord",
    "PriorSkillRegistry",
    "ProceduralMemoryRecord",
    "ProceduralMemoryRegistry",
    "SemanticMemoryRecord",
    "SemanticMemoryRegistry",
    "SkillProvenance",
    "load_inherited_prior_registry",
]
