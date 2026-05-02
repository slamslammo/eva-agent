"""Minimal cognitive-memory stub builder for the Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import DeliberationInput, MemoryWriteStub, ReleaseDecision


def build_memory_stub(
    recorded_at: str,
    deliberation_input: DeliberationInput,
    release_decision: ReleaseDecision,
) -> MemoryWriteStub | None:
    """Build a selective memory write stub from current L3 context."""

    signal_summary = deliberation_input.signal_batch.get("summary", {})
    if bool(signal_summary.get("has_threat_signal", False)):
        salience = "elevated"
        memory_type = "threat_trace"
        write_reason = "threat_signal_present"
    elif release_decision.outcome != "withhold":
        salience = "focused"
        memory_type = "release_trace"
        write_reason = f"release_outcome={release_decision.outcome}"
    else:
        return None
    return MemoryWriteStub(
        recorded_at=recorded_at,
        source="l3_deliberation",
        salience=salience,
        memory_type=memory_type,
        write_reason=write_reason,
        linked_audit_recorded_at=recorded_at,
        content={
            "top_drive": deliberation_input.drive_broadcast.get("top_drive"),
            "signal_summary": dict(signal_summary),
            "runtime_gate_context": dict(deliberation_input.runtime_gate_context),
            "release_outcome": release_decision.outcome,
            "selected_action": release_decision.selected_action,
            "candidate_profile": release_decision.release_context.get("candidate_profile"),
        },
    )
