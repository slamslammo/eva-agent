"""Runtime assembly for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import ActivePressureTable, to_iso8601
from .anchors import apply_structural_anchors
from .candidates import build_candidates
from .contracts import DeliberationAuditRecord, DeliberationInput
from .mediator import decide_release
from .memory import build_memory_stub
from .value import assess_candidates


def build_deliberation_input(
    signal_batch: dict[str, Any],
    drive_broadcast: dict[str, Any],
    runtime_gate_context: dict[str, Any],
    pressure_table: ActivePressureTable | dict[str, Any] | None = None,
) -> DeliberationInput:
    """Assemble the frozen L3 input from B0 contracts and optional pressure context."""

    pressure_payload: dict[str, Any] | None = None
    if isinstance(pressure_table, ActivePressureTable):
        pressure_payload = pressure_table.to_dict()
    elif isinstance(pressure_table, dict):
        pressure_payload = dict(pressure_table)
    return DeliberationInput(
        signal_batch=dict(signal_batch),
        drive_broadcast=dict(drive_broadcast),
        runtime_gate_context=dict(runtime_gate_context),
        compatibility_pressure_table=pressure_payload,
    )


def run_deliberation(now: datetime, deliberation_input: DeliberationInput) -> tuple[DeliberationAuditRecord, dict[str, Any] | None]:
    """Run the minimal L3 pass and return audit plus optional memory-stub payloads."""

    recorded_at = to_iso8601(now) or now.isoformat()
    candidates = apply_structural_anchors(build_candidates(deliberation_input), deliberation_input)
    assessments = assess_candidates(candidates, deliberation_input)
    release_decision = decide_release(assessments)
    memory_stub = build_memory_stub(recorded_at, deliberation_input, release_decision)
    audit_record = DeliberationAuditRecord(
        recorded_at=recorded_at,
        deliberation_input=deliberation_input.to_dict(),
        candidates=[candidate.to_dict() for candidate in candidates],
        assessments=[assessment.to_dict() for assessment in assessments],
        release_decision=release_decision.to_dict(),
    )
    return audit_record, None if memory_stub is None else memory_stub.to_dict()
