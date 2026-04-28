"""Phase B minimal L3 contracts built on top of the B0 input surfaces."""

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the assembled L3 input."""

        payload = {
            "signal_batch": dict(self.signal_batch),
            "drive_broadcast": dict(self.drive_broadcast),
            "runtime_gate_context": dict(self.runtime_gate_context),
        }
        if self.compatibility_pressure_table is not None:
            payload["compatibility_pressure_table"] = dict(self.compatibility_pressure_table)
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

    def to_dict(self) -> dict[str, Any]:
        """Serialize one candidate assessment."""

        return {
            "candidate_id": self.candidate_id,
            "action": self.action,
            "score": self.score,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class ReleaseDecision:
    """Mediator release output with default inhibition semantics."""

    outcome: str
    selected_action: str | None = None
    selected_candidate_id: str | None = None
    rationale: tuple[str, ...] = ()
    release_context: dict[str, Any] = field(default_factory=dict)

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
