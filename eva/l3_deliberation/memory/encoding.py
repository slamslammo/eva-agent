"""Canonical episodic encoding helpers plus bounded learning re-exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts import DeliberationInput, ReleaseDecision
from ..peer_circuit.rpe import LearningOutcomeRecord, build_learning_outcome_record, evaluate_response_outcome
from .retrieval import pressure_reason_from_input
from .skill_library import build_situation_key_from_values

__all__ = [
    "LearningOutcomeRecord",
    "MemoryWriteStub",
    "build_learning_outcome_record",
    "build_memory_stub",
    "evaluate_response_outcome",
]


@dataclass(frozen=True)
class MemoryWriteStub:
    """Canonical episodic-memory write payload emitted by L3."""

    recorded_at: str
    source: str
    salience: float
    memory_type: str
    write_reason: str
    linked_audit_recorded_at: str
    content: dict[str, Any]

    def __post_init__(self) -> None:
        """Normalize the append-only payload before persistence."""

        object.__setattr__(self, "salience", _normalized_salience(self.salience))
        object.__setattr__(self, "content", dict(self.content))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the episodic memory payload."""

        return {
            "recorded_at": self.recorded_at,
            "source": self.source,
            "salience": self.salience,
            "memory_type": self.memory_type,
            "write_reason": self.write_reason,
            "linked_audit_recorded_at": self.linked_audit_recorded_at,
            "content": dict(self.content),
        }


def build_memory_stub(
    recorded_at: str,
    deliberation_input: DeliberationInput,
    release_decision: ReleaseDecision | dict[str, Any],
) -> MemoryWriteStub | None:
    """Build one episodic memory payload from the current deliberation boundary."""

    release = release_decision.to_dict() if isinstance(release_decision, ReleaseDecision) else dict(release_decision)
    signal_summary = deliberation_input.signal_batch.get("summary", {})
    has_threat_signal = bool(signal_summary.get("has_threat_signal", False))
    release_outcome = str(release.get("outcome") or "withhold")
    release_context = release.get("release_context") or {}
    if has_threat_signal:
        memory_type = "threat_trace"
        write_reason = "threat_signal_present"
    elif release_outcome != "withhold":
        memory_type = "release_trace"
        write_reason = f"release_outcome={release_outcome}"
    else:
        return None
    drive_state_at_encoding = _drive_state_at_encoding(deliberation_input)
    pressure_reason = _pressure_reason_for_encoding(deliberation_input)
    situation_key = _situation_key_for_encoding(
        top_drive=drive_state_at_encoding["top_drive"],
        life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
        pressure_reason=pressure_reason,
    )
    return MemoryWriteStub(
        recorded_at=recorded_at,
        source="l3_deliberation",
        salience=_memory_salience(deliberation_input, release_outcome=release_outcome, has_threat_signal=has_threat_signal),
        memory_type=memory_type,
        write_reason=write_reason,
        linked_audit_recorded_at=recorded_at,
        content={
            "top_drive": drive_state_at_encoding["top_drive"],
            "pressure_reason": pressure_reason,
            "situation_key": situation_key,
            "signal_summary": dict(signal_summary),
            "runtime_gate_context": dict(deliberation_input.runtime_gate_context),
            "release_outcome": release_outcome,
            "selected_action": release.get("selected_action"),
            "candidate_profile": release_context.get("candidate_profile") if isinstance(release_context, dict) else None,
            "drive_state_at_encoding": drive_state_at_encoding,
        },
    )


def _memory_salience(
    deliberation_input: DeliberationInput,
    *,
    release_outcome: str,
    has_threat_signal: bool,
) -> float:
    """Return continuous salience for one encoding event."""

    drive_state = _drive_state_at_encoding(deliberation_input)
    top_drive = drive_state["top_drive"]
    drive_levels = drive_state["drive_levels"]
    top_drive_level = _coerced_probability(drive_levels.get(top_drive, 0.0))
    salience = 0.25 + (0.5 * top_drive_level)
    if has_threat_signal:
        threat_signal_count = int(deliberation_input.signal_batch.get("summary", {}).get("threat_signal_count", 0))
        salience += 0.25 + min(0.15, 0.05 * max(threat_signal_count, 0))
    elif release_outcome != "withhold":
        salience += 0.1
    return _normalized_salience(salience)


def _drive_state_at_encoding(deliberation_input: DeliberationInput) -> dict[str, Any]:
    """Capture the bounded drive snapshot attached to this encoding event."""

    drive_broadcast = deliberation_input.drive_broadcast
    drive_levels = drive_broadcast.get("drive_levels")
    drive_trends = drive_broadcast.get("drive_trends")
    return {
        "top_drive": str(drive_broadcast.get("top_drive") or "unknown"),
        "drive_levels": dict(drive_levels) if isinstance(drive_levels, dict) else {},
        "drive_trends": dict(drive_trends) if isinstance(drive_trends, dict) else {},
    }


def _pressure_reason_for_encoding(deliberation_input: DeliberationInput) -> str:
    """Return the bounded pressure reason attached to one encoding event."""

    return pressure_reason_from_input(deliberation_input)


def _situation_key_for_encoding(*, top_drive: str, life_state: str, pressure_reason: str) -> str:
    """Return the compact situation key attached to one encoding event."""

    return build_situation_key_from_values(
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
    )


def _normalized_salience(value: Any) -> float:
    """Clamp one salience value into the persisted 0-1 range."""

    return round(max(0.0, min(1.0, float(value))), 3)


def _coerced_probability(value: Any) -> float:
    """Coerce an arbitrary drive level into the bounded 0-1 range."""

    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
