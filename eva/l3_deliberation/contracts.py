"""Phase B / early Phase C L3 contracts built on top of the B0 input surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..kernel import ActivePressureTable

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


def _pressure_payload(
    pressure_table: ActivePressureTable | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Normalize optional compatibility pressure context into a frozen payload."""

    if isinstance(pressure_table, ActivePressureTable):
        return pressure_table.to_dict()
    if isinstance(pressure_table, dict):
        return dict(pressure_table)
    return None


def build_deliberation_input(
    signal_batch: dict[str, Any],
    drive_broadcast: dict[str, Any],
    runtime_gate_context: dict[str, Any],
    pressure_table: ActivePressureTable | dict[str, Any] | None = None,
    *,
    working_memory_context: dict[str, Any] | None = None,
) -> "DeliberationInput":
    """Assemble the frozen L3 input from B0 contracts and optional pressure context."""

    return DeliberationInput(
        signal_batch=dict(signal_batch),
        drive_broadcast=dict(drive_broadcast),
        runtime_gate_context=dict(runtime_gate_context),
        compatibility_pressure_table=_pressure_payload(pressure_table),
        working_memory_context=None if working_memory_context is None else dict(working_memory_context),
    )


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
    drive_impact_schema: dict[str, float] = field(default_factory=dict)
    side_effect_class: str = "compatibility_side_effect"

    def to_dict(self) -> dict[str, Any]:
        """Serialize one structured candidate."""

        payload = {
            "candidate_id": self.candidate_id,
            "capability": self.capability,
            "action": self.action,
            "parameter_domain": dict(self.parameter_domain),
            "justification": list(self.justification),
        }
        if self.drive_impact_schema:
            payload["drive_impact_schema"] = dict(self.drive_impact_schema)
        if self.side_effect_class != "compatibility_side_effect":
            payload["side_effect_class"] = self.side_effect_class
        return payload


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
class ReleaseToken:
    """Runtime-only release authority threaded from mediator to tool-edge."""

    token_id: str
    outcome: str
    candidate_id: str
    candidate_profile: str


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
    release_token: ReleaseToken | None = None

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
    release_token: ReleaseToken | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the deliberation audit record."""

        return {
            "recorded_at": self.recorded_at,
            "deliberation_input": dict(self.deliberation_input),
            "candidates": [dict(candidate) for candidate in self.candidates],
            "assessments": [dict(assessment) for assessment in self.assessments],
            "release_decision": dict(self.release_decision),
        }


def build_deliberation_audit_record(
    recorded_at: str,
    deliberation_input: DeliberationInput,
    candidates: list[Candidate],
    assessments: list[CandidateAssessment],
    release_decision: ReleaseDecision,
) -> DeliberationAuditRecord:
    """Build the append-only L3 deliberation audit artifact from current pass artifacts."""

    return DeliberationAuditRecord(
        recorded_at=recorded_at,
        deliberation_input=deliberation_input.to_dict(),
        candidates=[candidate.to_dict() for candidate in candidates],
        assessments=[assessment.to_dict() for assessment in assessments],
        release_decision=release_decision.to_dict(),
        release_token=release_decision.release_token,
    )
