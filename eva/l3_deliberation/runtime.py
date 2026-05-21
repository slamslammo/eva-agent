"""Runtime assembly for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import StateStore, to_iso8601
from ..anchor import build_action_domain
from .contracts import DeliberationAuditRecord, DeliberationInput, build_deliberation_audit_record, build_deliberation_input
from .memory import WorkingMemoryAdapter, build_memory_stub
from .peer_circuit import decide_release
from .reasoning import assess_candidates, build_candidates, build_working_memory_context_from_store
from .reasoning.proposer import Proposer, normalize_proposals

def build_deliberation_input_from_store(
    store: StateStore,
    signal_batch: dict[str, Any],
    drive_broadcast: dict[str, Any],
    runtime_gate_context: dict[str, Any],
    pressure_table: ActivePressureTable | dict[str, Any] | None = None,
    *,
    working_memory_backend: str = "local_rule_based",
    llm_adapter: WorkingMemoryAdapter | None = None,
    working_memory_advisory_source: str | None = None,
    response_history: list[dict[str, Any]] | None = None,
) -> DeliberationInput:
    """Assemble deliberation input and attach optional working-memory context from the store."""

    base_input = build_deliberation_input(
        signal_batch,
        drive_broadcast,
        runtime_gate_context,
        pressure_table,
    )
    working_memory_context = build_working_memory_context_from_store(
        store,
        base_input,
        backend=working_memory_backend,
        llm_adapter=llm_adapter,
        advisory_source=working_memory_advisory_source,
        response_history=response_history,
    ).to_dict()
    return build_deliberation_input(
        signal_batch,
        drive_broadcast,
        runtime_gate_context,
        pressure_table,
        working_memory_context=working_memory_context,
    )


def run_deliberation(
    now: datetime,
    deliberation_input: DeliberationInput,
    *,
    proposer: Proposer | None = None,
) -> tuple[DeliberationAuditRecord, dict[str, Any] | None]:
    """Run the minimal L3 pass and return audit plus optional memory-stub payloads.

    Round 1.E: an optional ``proposer`` shapes the considered candidate set within
    the anchor-admitted domain (between admission and assessment). With ``proposer``
    None the pass is byte-identical to pre-1.E (behavior-preserving). The proposer
    only shapes *what is considered* — selection (peer-circuit) and release
    (mediator) authority below are unchanged; a proposal is never a release.
    """

    recorded_at = to_iso8601(now) or now.isoformat()
    action_domain = build_action_domain(deliberation_input)
    proposals_payload: list[dict[str, Any]] = []
    rejected_payload: list[dict[str, Any]] = []
    if proposer is None:
        candidates = build_candidates(action_domain)
    else:
        proposals = proposer.propose(deliberation_input.working_memory_context or {}, action_domain)
        normalized = normalize_proposals(proposals, action_domain)
        # Safety net: never starve the mediator — fall back to the full admitted
        # set if shaping yielded nothing.
        candidates = normalized.candidates or build_candidates(action_domain)
        proposals_payload = [proposal.to_dict() for proposal in proposals]
        rejected_payload = list(normalized.rejections)
    assessments = assess_candidates(candidates, deliberation_input)
    release_decision = decide_release(
        assessments,
        working_memory_context=deliberation_input.working_memory_context,
    )
    memory_stub = build_memory_stub(recorded_at, deliberation_input, release_decision)
    audit_record = build_deliberation_audit_record(
        recorded_at,
        deliberation_input,
        candidates,
        assessments,
        release_decision,
        proposals=proposals_payload,
        rejected_proposals=rejected_payload,
    )
    return audit_record, None if memory_stub is None else memory_stub.to_dict()
