"""Phase B / early Phase C L3 contracts built on top of the B0 input surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

REQUIRED_SIGNAL_BATCH_KEYS = frozenset({"signals", "summary"})
REQUIRED_RUNTIME_GATE_KEYS = frozenset({"instance_valid", "turn_allowed", "critical_blocked", "conservative_mode", "life_state"})
REQUIRED_DRIVE_BROADCAST_KEYS = frozenset({"top_drive", "drive_levels", "drive_trends"})


def _validated_contract_dict(payload: dict[str, Any], required_keys: frozenset[str], *, contract_name: str) -> dict[str, Any]:
    """Validate one contract payload before freezing it into L3 input."""

    normalized = dict(payload)
    missing = sorted(required_keys.difference(normalized))
    if missing:
        raise ValueError(f"{contract_name} missing required keys: {', '.join(missing)}")
    return normalized


@dataclass(frozen=True)
class DeliberationInput:
    """Frozen L3 input assembled from the B0 runtime contracts."""

    signal_batch: dict[str, Any]
    drive_broadcast: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    compatibility_pressure_table: dict[str, Any] | None = None
    working_memory_context: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate that the canonical B0 inputs are present and complete."""

        object.__setattr__(
            self,
            "signal_batch",
            _validated_contract_dict(self.signal_batch, REQUIRED_SIGNAL_BATCH_KEYS, contract_name="signal_batch"),
        )
        object.__setattr__(
            self,
            "drive_broadcast",
            _validated_contract_dict(self.drive_broadcast, REQUIRED_DRIVE_BROADCAST_KEYS, contract_name="drive_broadcast"),
        )
        object.__setattr__(
            self,
            "runtime_gate_context",
            _validated_contract_dict(
                self.runtime_gate_context,
                REQUIRED_RUNTIME_GATE_KEYS,
                contract_name="runtime_gate_context",
            ),
        )
        if self.compatibility_pressure_table is not None:
            object.__setattr__(self, "compatibility_pressure_table", dict(self.compatibility_pressure_table))
        if self.working_memory_context is not None:
            object.__setattr__(self, "working_memory_context", dict(self.working_memory_context))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the assembled L3 input."""

        payload = {
            "signal_batch": dict(self.signal_batch),
            "drive_broadcast": dict(self.drive_broadcast),
            "runtime_gate_context": dict(self.runtime_gate_context),
        }
        if self.compatibility_pressure_table is not None:
            payload["compatibility_pressure_table"] = dict(self.compatibility_pressure_table)
        if self.working_memory_context is not None:
            payload["working_memory_context"] = dict(self.working_memory_context)
        return payload


@dataclass(frozen=True)
class Candidate:
    """One structured candidate before value judgment and release gating."""

    candidate_id: str
    capability: str
    action: str
    parameter_domain: dict[str, Any] = field(default_factory=dict)
    justification: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize one structured candidate."""

        return {
            "candidate_id": self.candidate_id,
            "capability": self.capability,
            "action": self.action,
            "parameter_domain": dict(self.parameter_domain),
            "justification": list(self.justification),
        }


@dataclass(frozen=True)
class CandidateAssessment:
    """Rule-based value judgment result for one candidate."""

    candidate_id: str
    action: str
    score: float
    disposition: str
    reasons: tuple[str, ...] = ()
    learning_bias: float = 0.0
    bias_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize one candidate assessment."""

        payload = {
            "candidate_id": self.candidate_id,
            "action": self.action,
            "score": self.score,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
        }
        if self.learning_bias != 0.0:
            payload["learning_bias"] = self.learning_bias
        if self.bias_reasons:
            payload["bias_reasons"] = list(self.bias_reasons)
        return payload


@dataclass(frozen=True)
class ReleaseDecision:
    """Mediator release output with default inhibition semantics."""

    outcome: str
    selected_action: str | None = None
    selected_candidate_id: str | None = None
    rationale: tuple[str, ...] = ()
    release_context: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str | None = None
    learning_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the mediator decision."""

        payload = {
            "outcome": self.outcome,
            "rationale": list(self.rationale),
        }
        if self.selected_action is not None:
            payload["selected_action"] = self.selected_action
        if self.selected_candidate_id is not None:
            payload["selected_candidate_id"] = self.selected_candidate_id
        if self.release_context:
            payload["release_context"] = dict(self.release_context)
        if self.expected_outcome is not None:
            payload["expected_outcome"] = self.expected_outcome
        if self.learning_context:
            payload["learning_context"] = dict(self.learning_context)
        return payload


@dataclass(frozen=True)
class DeliberationAuditRecord:
    """Append-only audit record for one L3 deliberation pass."""

    recorded_at: str
    deliberation_input: dict[str, Any]
    candidates: list[dict[str, Any]]
    assessments: list[dict[str, Any]]
    release_decision: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the deliberation audit record."""

        return {
            "recorded_at": self.recorded_at,
            "deliberation_input": dict(self.deliberation_input),
            "candidates": [dict(candidate) for candidate in self.candidates],
            "assessments": [dict(assessment) for assessment in self.assessments],
            "release_decision": dict(self.release_decision),
        }


@dataclass(frozen=True)
class MemoryWriteStub:
    """Minimal cognitive-memory write payload emitted by L3."""

    recorded_at: str
    source: str
    salience: str
    memory_type: str
    write_reason: str
    linked_audit_recorded_at: str
    content: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the memory stub payload."""

        return {
            "recorded_at": self.recorded_at,
            "source": self.source,
            "salience": self.salience,
            "memory_type": self.memory_type,
            "write_reason": self.write_reason,
            "linked_audit_recorded_at": self.linked_audit_recorded_at,
            "content": dict(self.content),
        }


@dataclass(frozen=True)
class LearningOutcomeRecord:
    """Append-only Phase C learning record linking release intent to actual outcome."""

    recorded_at: str
    source: str
    linked_audit_recorded_at: str
    linked_response_id: str | None = None
    selected_action: str | None = None
    candidate_profile: str | None = None
    response_mode: str | None = None
    pressure_id: str | None = None
    pressure_type: str | None = None
    pressure_reason: str | None = None
    expected_outcome: str = "unknown"
    observed_outcome: str = "unknown"
    outcome_delta: float = 0.0
    rpe_like_score: float = 0.0
    evaluation_label: str = "uncertain"
    confidence: float = 0.0
    content: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the learning outcome payload."""

        payload = {
            "recorded_at": self.recorded_at,
            "source": self.source,
            "linked_audit_recorded_at": self.linked_audit_recorded_at,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "outcome_delta": self.outcome_delta,
            "rpe_like_score": self.rpe_like_score,
            "evaluation_label": self.evaluation_label,
            "confidence": self.confidence,
            "content": dict(self.content),
        }
        if self.linked_response_id is not None:
            payload["linked_response_id"] = self.linked_response_id
        if self.selected_action is not None:
            payload["selected_action"] = self.selected_action
        if self.candidate_profile is not None:
            payload["candidate_profile"] = self.candidate_profile
        if self.response_mode is not None:
            payload["response_mode"] = self.response_mode
        if self.pressure_id is not None:
            payload["pressure_id"] = self.pressure_id
        if self.pressure_type is not None:
            payload["pressure_type"] = self.pressure_type
        if self.pressure_reason is not None:
            payload["pressure_reason"] = self.pressure_reason
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
