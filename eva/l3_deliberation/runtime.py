"""Runtime assembly for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

from ..kernel import StateStore, to_iso8601
from ..anchor import build_action_domain
from .contracts import (
    Candidate,
    DeliberationAuditRecord,
    DeliberationInput,
    ReleaseDecision,
    build_deliberation_audit_record,
    build_deliberation_input,
)
from .memory import WorkingMemoryAdapter, build_memory_stub
from .peer_circuit import decide_release
from .reasoning import assess_candidates, build_working_memory_context_from_store
from .reasoning.candidate_producer import CandidateProducer, HeuristicCandidateProducer

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
    producer: CandidateProducer | None = None,
) -> tuple[DeliberationAuditRecord, dict[str, Any] | None]:
    """Run the minimal L3 pass and return audit plus optional memory-stub payloads.

    Round 1.G: the dlPFC candidate *producer* forms the candidate set within the
    anchor-bounded domain (theory v0.5 §8.6.3 / blueprint §7.4). ``producer`` None
    defaults to the deterministic ``HeuristicCandidateProducer`` (= pre-1.G behavior),
    so ``local_rule_based`` / model-off is behavior-preserving; the live-LLM producer
    (phase 2) injects here. Selection (peer-circuit) + release (mediator) authority
    below are unchanged — the producer only forms candidates, never releases.
    """

    recorded_at = to_iso8601(now) or now.isoformat()
    action_domain = build_action_domain(deliberation_input)
    active_producer = producer or HeuristicCandidateProducer()
    candidates = active_producer.produce(action_domain, deliberation_input)
    assessments = assess_candidates(candidates, deliberation_input)
    release_decision = decide_release(
        assessments,
        working_memory_context=deliberation_input.working_memory_context,
    )
    release_decision = _thread_selected_action_hint(release_decision, candidates)
    memory_stub = build_memory_stub(recorded_at, deliberation_input, release_decision)
    audit_record = build_deliberation_audit_record(
        recorded_at,
        deliberation_input,
        candidates,
        assessments,
        release_decision,
    )
    return audit_record, None if memory_stub is None else memory_stub.to_dict()


def _thread_selected_action_hint(
    release_decision: ReleaseDecision,
    candidates: list[Candidate],
) -> ReleaseDecision:
    """Carry the selected candidate's ``action_hint`` into ``release_context``.

    Round 1.G phase 2 (a): drive decides the posture (the mediator's frozen
    OFC-max selection picks ``selected_candidate_id``); within that posture the
    dlPFC producer's concrete-action lever is the selected candidate's
    ``action_hint``. The mediator does not carry candidate-level data, so once it
    has chosen, we look the winner up by id and fold its hint into the
    scenario-facing ``release_context`` (where the Crafter bridge consumes it,
    prioritizing it over ``PROFILE_DEFAULT_ACTION`` / prior).

    This never changes release authority or default inhibition — ``outcome``,
    ``selected_candidate_id`` and ``release_token`` are untouched; it only
    enriches ``release_context``, exactly as lifecycle's
    ``_release_context_with_observation`` already does downstream. When the
    selected candidate has no hint (heuristic / model-off), the decision is
    returned unchanged → byte-identical.
    """

    selected_id = release_decision.selected_candidate_id
    if not selected_id:
        return release_decision
    hint = next(
        (
            candidate.action_hint
            for candidate in candidates
            if candidate.candidate_id == selected_id and candidate.action_hint
        ),
        None,
    )
    # For raw-action candidates the concrete execution target is candidate.action itself
    # (action_hint is empty); thread it so the bridge can read the released action.
    if not hint:
        hint = next(
            (
                candidate.action
                for candidate in candidates
                if candidate.candidate_id == selected_id
                and getattr(candidate, "capability", "") == "raw_action"
                and candidate.action
            ),
            None,
        )
    if not hint:
        return release_decision
    release_context = dict(release_decision.release_context)
    release_context["action_hint"] = hint
    return dataclasses.replace(release_decision, release_context=release_context)
