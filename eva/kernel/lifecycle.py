"""Heartbeat-first lifecycle runtime owned by the kernel namespace."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Protocol

from .config import ExternalLifeConfig, LifecycleConfig
from .instance import InstanceGuard, InstanceSnapshot
from .state import EventRecord, RuntimeState, StateStore, emit_log_line, utc_now
from ..l1_sensing.patrol import PatrolScheduler, execute_patrol
from ..l1_sensing.sensor_registry import SensorRegistry
from ..l2_drive.reflex import build_protective_reflex
from ..l3_deliberation import (
    WorkingMemoryAdapter,
    build_deliberation_input_from_store,
    build_learning_outcome_record,
    run_deliberation,
    summarize_habit_bias,
)
from ..l3_deliberation.contracts import DeliberationAuditRecord, ReleaseDecision, ReleaseToken
from ..l3_deliberation.reasoning.candidate_producer import CandidateProducer
from ..observability import NullTraceSink, TraceSink, reset_current_trace, set_current_trace
from ..l3_deliberation.memory import (
    append_cognitive_memory_stub,
    append_habit_bias,
    append_learning_outcome,
    read_learning_outcomes,
)
from ..l3_deliberation.tool_edge import build_response_selected_event_details, maybe_respond_after_patrol

__all__ = [
    "LifeState",
    "TickResult",
    "WorkSlice",
    "TurnResult",
    "LifecycleRuntime",
    "build_runtime_gate_context",
]


def build_runtime_gate_context(
    state: RuntimeState,
    *,
    instance_valid: bool,
    critical_blocked: bool,
    conservative_mode: bool,
    seconds_to_heartbeat: float | None = None,
) -> dict[str, Any]:
    """Build the minimal kernel gate context exposed to downstream layers."""

    return {
        "instance_valid": instance_valid,
        "turn_allowed": instance_valid and not critical_blocked,
        "critical_blocked": critical_blocked,
        "conservative_mode": conservative_mode,
        "life_state": state.life_state,
        "seconds_to_heartbeat": 0.0 if seconds_to_heartbeat is None else max(float(seconds_to_heartbeat), 0.0),
    }


def _release_context_with_observation(
    release_context: dict[str, Any] | None,
    extra_shared_facts: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Thread the turn's bounded ``agent_observation`` into the release context.

    Fix-B: action-candidate generation needs the agent's local view to pursue
    targets, but the observation otherwise stops at the sensing layer. Inject it
    into ``candidate_context`` (without clobbering an existing one) so the
    scenario action bridge can resolve observation-directed actions. Returns the
    release context unchanged when there is no observation to add.
    """

    agent_observation = (
        extra_shared_facts.get("agent_observation") if isinstance(extra_shared_facts, dict) else None
    )
    if not isinstance(release_context, dict) or not isinstance(agent_observation, dict):
        return release_context
    augmented = dict(release_context)
    candidate_context = dict(augmented.get("candidate_context") or {})
    candidate_context.setdefault("agent_observation", agent_observation)
    augmented["candidate_context"] = candidate_context
    return augmented


class LifeState(str, Enum):
    """Coarse-grained health states for the life loop."""

    RECOVERING = "RECOVERING"
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class TickResult:
    """Summary of one completed heartbeat tick."""

    tick_id: str
    life_state: LifeState
    instance_valid: bool
    heartbeat_age_sec: float
    consecutive_failures: int


@dataclass(frozen=True)
class WorkSlice:
    """One unit of turn work, either maintenance or patrol."""

    name: str
    kind: str = "maintenance"
    due_at: datetime | None = None


@dataclass
class TurnResult:
    """Summary of one attempted turn execution."""

    turn_id: str
    executed: bool
    yielded_to_heartbeat: bool
    work_slice: str | None = None
    work_kind: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class ExternalActionRuntime(Protocol):
    """Scenario-owned bounded action stepping surface used by lifecycle."""

    def step_action(self, action_name: str) -> Any: ...


class LifecycleRuntime:
    """Run the heartbeat loop while preserving heartbeat priority over turn work."""

    def __init__(
        self,
        store: StateStore,
        instance_guard: InstanceGuard,
        lifecycle: LifecycleConfig,
        external_life: ExternalLifeConfig | None = None,
        working_memory_backend: str = "local_rule_based",
        working_memory_adapter: WorkingMemoryAdapter | None = None,
        working_memory_advisory_source: str | None = None,
        sensor_registry: SensorRegistry | None = None,
        extra_shared_facts_provider: Callable[[], dict[str, Any] | None] | None = None,
        action_runtime: ExternalActionRuntime | None = None,
        candidate_producer: CandidateProducer | None = None,
        trace_sink: TraceSink | None = None,
    ) -> None:
        self.store = store
        self.instance_guard = instance_guard
        self.lifecycle = lifecycle
        self.external_life = external_life or ExternalLifeConfig()
        self.working_memory_backend = working_memory_backend
        self.working_memory_adapter = working_memory_adapter
        self.working_memory_advisory_source = working_memory_advisory_source
        self.sensor_registry = sensor_registry
        self.extra_shared_facts_provider = extra_shared_facts_provider
        self.action_runtime = action_runtime
        # Round 1.G phase 2 (a): the live dlPFC candidate producer (action_hint
        # lever). ``None`` -> run_deliberation defaults to the deterministic
        # HeuristicCandidateProducer (model-off byte-equivalent).
        self.candidate_producer = candidate_producer
        # Round 1.H: opt-in cognitive-trace sink. ``None`` -> NullTraceSink (no-op,
        # byte-equivalent). H-2/H-3 emit transform/snapshot events from runtime seams.
        self.trace_sink: TraceSink = trace_sink or NullTraceSink()
        # Monotonic trace turn index (one per deliberating turn); events within a
        # turn share it so the viewer replays them aligned. Only advanced when tracing.
        self._trace_turn_index = 0
        self.patrol_scheduler = PatrolScheduler(self.external_life)
        self.pending_work: deque[WorkSlice] = deque([
            WorkSlice(name="self_check"),
            WorkSlice(name="persist_marker"),
        ])
        self._conservative_until_next_patrol = False
        self._tick_counter = 0
        self._turn_counter = 0

    def _emit_p1a_seam_trace(
        self,
        deliberation_input: Any,
        deliberation_audit: DeliberationAuditRecord,
        extra_shared_facts: dict[str, Any] | None = None,
        patrol_snapshot: Any = None,
    ) -> None:
        """Round 1.H H-2a/b/d: emit the seam-assembled P1a batch-1 transforms.

        Assembled purely from data the deliberation pass + patrol already returned —
        no frozen-owner function body is touched (red-line #2). Only called when
        ``trace_sink.enabled``; ``_trace_turn_index`` advances only while tracing,
        so a non-traced run is byte-identical. Covers ``l1.raw_observation`` (H-2b,
        from ``extra_shared_facts``), ``l1.threshold_classify`` + ``l1.rate_sense``
        (H-2d, from ``patrol_snapshot.dimensions`` status/evidence — seam-visible, no
        owner-hook), ``l1.signal_publish`` / ``l2.broadcast`` / ``anchor.admit`` +
        ``drive_state`` snapshot (H-2a). The ``l2.approach_delta`` owner-hook (H-2c)
        emits separately from drive_state during patrol with the same turn_index.
        """

        # turn_index is allocated once per patrol turn (set_current_trace below)
        # and shared by patrol-time owner hooks + this seam emit; advanced at turn end.
        turn_index = self._trace_turn_index
        agent_observation = (
            extra_shared_facts.get("agent_observation")
            if isinstance(extra_shared_facts, dict)
            else None
        )
        if isinstance(agent_observation, dict):
            visible = agent_observation.get("visible") if isinstance(agent_observation.get("visible"), dict) else {}
            self.trace_sink.emit_raw_observation(
                turn_index=turn_index,
                episode_step=agent_observation.get("step") if isinstance(agent_observation.get("step"), int) else None,
                payload={
                    "episode_id": agent_observation.get("episode_id"),
                    "step": agent_observation.get("step"),
                    "local_view": visible.get("local_view"),
                    "facing": visible.get("facing"),
                    "life_panel": visible.get("life_panel"),
                    "inventory_panel": visible.get("inventory_panel"),
                },
            )
        gate = dict(getattr(deliberation_input, "runtime_gate_context", {}) or {})
        gate_inputs = {
            key: gate.get(key)
            for key in ("instance_valid", "turn_allowed", "critical_blocked", "conservative_mode", "life_state")
        }
        signal_batch = dict(getattr(deliberation_input, "signal_batch", {}) or {})
        summary = signal_batch.get("summary") if isinstance(signal_batch.get("summary"), dict) else {}
        drive = dict(getattr(deliberation_input, "drive_broadcast", {}) or {})
        drive_levels = drive.get("drive_levels") if isinstance(drive.get("drive_levels"), dict) else {}

        # H-2d: dimension threshold classification + rate sensing are visible on the
        # patrol snapshot's DimensionSnapshots (status / evidence.reason / rate_context),
        # so they are seam-assembled here — no L1 owner-hook needed.
        dimensions = getattr(patrol_snapshot, "dimensions", None)
        if isinstance(dimensions, dict) and dimensions:
            classify: dict[str, Any] = {}
            rates: dict[str, Any] = {}
            for name, dim in dimensions.items():
                evidence = getattr(dim, "evidence", {}) or {}
                classify[str(name)] = {"status": getattr(dim, "status", None), "reason": evidence.get("reason")}
                if isinstance(evidence.get("rate_context"), dict):
                    rates[str(name)] = evidence["rate_context"]
            self.trace_sink.emit_transform(
                layer="L1",
                transform_id="l1.threshold_classify",
                code_anchor="scenarios/crafter/sensors/avatar_state.py",
                turn_index=turn_index,
                parents=[{"id": "l1.raw_observation", "edge_type": "pressure"}],
                outputs={"dimensions": classify},
            )
            if rates:
                self.trace_sink.emit_transform(
                    layer="L1",
                    transform_id="l1.rate_sense",
                    code_anchor="eva/l1_sensing/rate_sensors.py:build_rate_context",
                    turn_index=turn_index,
                    parents=[{"id": "l1.threshold_classify", "edge_type": "pressure"}],
                    outputs={"dimensions": rates},
                )

        self.trace_sink.emit_transform(
            layer="L1",
            transform_id="l1.signal_publish",
            code_anchor="eva/l1_sensing/signal_bus.py",
            turn_index=turn_index,
            inputs=gate_inputs,
            parents=[{"id": "l1.threshold_classify", "edge_type": "pressure"}],
            outputs={"summary": dict(summary)},
        )
        self.trace_sink.emit_transform(
            layer="L2",
            transform_id="l2.broadcast",
            code_anchor="eva/l2_drive/broadcast.py:build_drive_broadcast",
            turn_index=turn_index,
            parents=[{"id": "l1.signal_publish", "edge_type": "pressure"}],
            outputs={
                "top_drive": drive.get("top_drive"),
                "drive_levels": dict(drive_levels),
                "drive_trends": dict(drive.get("drive_trends") or {}),
            },
        )
        self.trace_sink.emit_snapshot(
            snapshot_type="drive_state",
            values=dict(drive_levels),
            turn_index=turn_index,
        )
        admitted = [
            {
                "candidate_id": candidate.get("candidate_id"),
                "candidate_profile": (candidate.get("parameter_domain") or {}).get("candidate_profile"),
                "action_hint": candidate.get("action_hint"),
            }
            for candidate in deliberation_audit.candidates
        ]
        self.trace_sink.emit_transform(
            layer="anchor",
            transform_id="anchor.admit",
            code_anchor="eva/anchor/domain_restriction.py:build_action_domain",
            turn_index=turn_index,
            inputs=gate_inputs,
            parents=[{"id": "l2.broadcast", "edge_type": "top_drive_bias"}],
            outputs={"admitted_candidates": admitted, "count": len(admitted)},
        )

        # H-3a: P1b batch-2 L3 chain — all seam-assembled from the deliberation audit
        # the pass already returned (candidates / assessments / release_decision). The
        # frozen owners (value_judgment OFC, mediator) are read, never modified.
        self.trace_sink.emit_transform(
            layer="L3",
            transform_id="l3.candidate_produce",
            code_anchor="eva/l3_deliberation/reasoning/llm_candidate_producer.py:LLMCandidateProducer.produce",
            turn_index=turn_index,
            parents=[{"id": "anchor.admit", "edge_type": "pressure"}],
            outputs={"candidates": admitted, "count": len(admitted)},
        )
        self.trace_sink.emit_transform(
            layer="L3",
            transform_id="l3.assess_score",
            code_anchor="eva/l3_deliberation/reasoning/value_judgment.py:assess_candidates",
            turn_index=turn_index,
            parents=[{"id": "l3.candidate_produce", "edge_type": "top_drive_bias"}],
            outputs={
                "assessments": [
                    {
                        "candidate_id": a.get("candidate_id"),
                        "action": a.get("action"),
                        "score": a.get("score"),
                        "disposition": a.get("disposition"),
                        "learning_bias": a.get("learning_bias"),
                    }
                    for a in deliberation_audit.assessments
                ]
            },
        )
        release = deliberation_audit.release_decision or {}
        self.trace_sink.emit_transform(
            layer="L3",
            transform_id="l3.decide_release",
            code_anchor="eva/l3_deliberation/peer_circuit/mediator.py:decide_release",
            turn_index=turn_index,
            parents=[{"id": "l3.assess_score", "edge_type": "pressure"}],
            outputs={
                "selected_candidate_id": release.get("selected_candidate_id"),
                "selected_action": release.get("selected_action"),
                "outcome": release.get("outcome"),
            },
        )
        self.trace_sink.emit_transform(
            layer="mediator",
            transform_id="mediator.release",
            code_anchor="eva/l3_deliberation/peer_circuit/mediator.py:decide_release",
            turn_index=turn_index,
            parents=[{"id": "l3.decide_release", "edge_type": "pressure"}],
            outputs={
                "outcome": release.get("outcome"),
                "release_authorized": deliberation_audit.release_token is not None,
                "action_hint": (release.get("release_context") or {}).get("action_hint"),
            },
        )

    def _emit_bridge_resolve_action_trace(self, response_summary: dict[str, Any] | None) -> None:
        """H-3a: emit ``bridge.resolve_action`` — the action_hint -> executed causal point.

        Read from the returned ``ResponseSelection`` summary (selected_action +
        selected_action_reason); the ``crafter_llm_action_hint_selection`` reason marks
        where the LLM action_hint drove the concrete action. No bridge body touched.
        """

        if not isinstance(response_summary, dict):
            return
        self.trace_sink.emit_transform(
            layer="bridge",
            transform_id="bridge.resolve_action",
            code_anchor="scenarios/crafter/actions/compatibility.py:select_response_action",
            turn_index=self._trace_turn_index,
            parents=[{"id": "mediator.release", "edge_type": "llm_advisory"}],
            outputs={
                "selected_action": response_summary.get("selected_action"),
                "selected_posture": response_summary.get("selected_posture"),
                "selected_action_reason": response_summary.get("selected_action_reason"),
            },
        )

    def activate_conservative_until_next_patrol(self) -> None:
        """Pause ordinary turn work until one later patrol finishes."""

        self._conservative_until_next_patrol = True

    def step_external_action(self, action_name: str) -> Any | None:
        """Delegate one bounded external action step to the scenario-owned runtime session."""

        if self.action_runtime is None or not hasattr(self.action_runtime, "step_action"):
            return None
        return self.action_runtime.step_action(action_name)

    def has_pending_work(self) -> bool:
        """Return whether the runtime has turn work waiting to execute."""

        return self._has_executable_work()

    def _has_executable_work(self) -> bool:
        """Return whether any queued work is currently executable."""

        return any(self._can_execute_work(work_slice) for work_slice in self.pending_work)

    def _can_execute_work(self, work_slice: WorkSlice) -> bool:
        """Return whether the current runtime mode allows this work slice."""

        if not self._conservative_until_next_patrol:
            return True
        return work_slice.kind == "patrol"

    def _pop_next_executable_work(self) -> WorkSlice | None:
        """Remove and return the next work slice allowed by the current mode."""

        if not self.pending_work:
            return None
        if not self._conservative_until_next_patrol:
            return self.pending_work.popleft()
        for work_slice in tuple(self.pending_work):
            if work_slice.kind == "patrol":
                self.pending_work.remove(work_slice)
                return work_slice
        return None

    def queue_due_patrols(self, now: datetime | None = None) -> None:
        """Append due patrol work slices without duplicating already queued cadences."""

        now = now or utc_now()
        queued_patrols = {work.name for work in self.pending_work if work.kind == "patrol"}
        for plan in self.patrol_scheduler.due_patrols(now, queued_patrols):
            self.pending_work.append(WorkSlice(name=plan.name, kind="patrol", due_at=plan.due_at))
            self.store.append_event(
                EventRecord(
                    event_type="patrol_queued",
                    timestamp=now,
                    details={
                        "cadence": plan.name,
                        "due_at": plan.due_at.isoformat(),
                    },
                )
            )
            emit_log_line("patrol_queued", cadence=plan.name, due_at=plan.due_at)

    def next_tick_id(self) -> str:
        """Return the next sequential tick id."""

        self._tick_counter += 1
        return f"tick-{self._tick_counter:04d}"

    def next_turn_id(self) -> str:
        """Return the next sequential turn id."""

        self._turn_counter += 1
        return f"turn-{self._turn_counter:04d}"

    def consume_distress_injection(self) -> dict[str, Any] | None:
        """Consume one manual distress injection payload if it exists."""

        path = self.store.paths.distress_injection_file
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8").strip()
        path.unlink(missing_ok=True)
        if not raw:
            return {"reason": "manual_distress_injection", "source": "distress_injection_file"}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"reason": "manual_distress_injection", "source": "distress_injection_file", "payload_parse_error": True}
        if not isinstance(payload, dict):
            return {"reason": "manual_distress_injection", "source": "distress_injection_file", "payload_parse_error": True}
        return {
            "reason": str(payload.get("reason") or "manual_distress_injection"),
            "source": "distress_injection_file",
        }

    def compute_life_state(
        self,
        state: RuntimeState,
        snapshot: InstanceSnapshot,
        now: datetime,
        *,
        force_critical: bool = False,
    ) -> LifeState:
        """Project the current life state from instance validity and heartbeat history."""

        if not snapshot.instance_valid:
            return LifeState.CRITICAL
        if force_critical:
            return LifeState.CRITICAL
        if state.recovering_until and now < state.recovering_until:
            return LifeState.RECOVERING
        if state.consecutive_failures >= self.lifecycle.critical_after_missed_beats:
            return LifeState.CRITICAL
        if state.consecutive_failures >= self.lifecycle.degraded_after_missed_beats:
            return LifeState.DEGRADED
        if state.last_heartbeat_at is None:
            return LifeState.RECOVERING
        heartbeat_age = (now - state.last_heartbeat_at).total_seconds()
        if heartbeat_age >= self.lifecycle.heartbeat_interval_sec * self.lifecycle.critical_after_missed_beats:
            return LifeState.CRITICAL
        if heartbeat_age >= self.lifecycle.heartbeat_interval_sec * self.lifecycle.degraded_after_missed_beats:
            return LifeState.DEGRADED
        return LifeState.STABLE

    def run_tick(self, state: RuntimeState, *, now: datetime | None = None) -> TickResult:
        """Run one heartbeat tick and refresh persistent runtime state."""

        now = now or utc_now()
        tick_id = self.next_tick_id()
        previous_life_state = state.life_state
        self.store.append_event(EventRecord(event_type="tick_started", timestamp=now, tick_id=tick_id))
        snapshot = self.instance_guard.snapshot(now)
        distress_injection = self.consume_distress_injection() if snapshot.instance_valid else None
        sampled_heartbeat_age_sec = 0.0 if state.last_heartbeat_at is None else max((now - state.last_heartbeat_at).total_seconds(), 0.0)
        life_state = self.compute_life_state(state, snapshot, now, force_critical=distress_injection is not None)
        active_record = self.instance_guard.refresh_lease() if snapshot.instance_valid else self.store.read_active_instance()
        state.last_tick_id = tick_id
        state.tick_ok = True
        state.state_io_ok = True
        state.instance_valid = snapshot.instance_valid
        state.life_state = life_state.value
        state.updated_at = now
        if snapshot.instance_valid:
            state.last_heartbeat_at = now
            state.heartbeat_age_sec = 0.0
            state.heartbeat_ok = True
            if life_state in {LifeState.STABLE, LifeState.RECOVERING}:
                state.consecutive_failures = 0
        else:
            state.heartbeat_age_sec = sampled_heartbeat_age_sec
            state.heartbeat_ok = False
            state.consecutive_failures += 1
        if state.recovering_until is None:
            state.recovering_until = now + timedelta(seconds=self.lifecycle.recovering_window_sec)
        self.store.write_runtime_state(state)
        lease_expires_at = snapshot.lease_expires_at if active_record is None else active_record.lease_expires_at
        generation = snapshot.generation if active_record is None else active_record.generation
        self.store.append_event(
            EventRecord(
                event_type="tick_completed",
                timestamp=now,
                tick_id=tick_id,
                life_state=life_state.value,
                details={
                    "instance_valid": snapshot.instance_valid,
                    "generation": generation,
                    "lease_expires_at": lease_expires_at.isoformat(),
                    "sampled_heartbeat_age_sec": sampled_heartbeat_age_sec,
                    "consecutive_failures": state.consecutive_failures,
                },
            )
        )
        emit_log_line(
            "tick",
            tick_id=tick_id,
            state=life_state.value,
            instance_valid=snapshot.instance_valid,
            heartbeat_age_sec=state.heartbeat_age_sec,
            consecutive_failures=state.consecutive_failures,
            generation=generation,
        )
        if previous_life_state != life_state.value:
            self.store.append_event(
                EventRecord(
                    event_type="life_state_changed",
                    timestamp=now,
                    tick_id=tick_id,
                    life_state=life_state.value,
                    details={"from": previous_life_state, "to": life_state.value},
                )
            )
            emit_log_line("transition", tick_id=tick_id, from_state=previous_life_state, to_state=life_state.value)
        if not snapshot.instance_valid:
            reason = snapshot.invalid_reasons[0] if snapshot.invalid_reasons else "instance_invalid"
            details = {
                "reason": reason,
                "life_state": life_state.value,
                "instance_valid": False,
                "consecutive_failures": state.consecutive_failures,
                "action_taken": "stop_turns_and_exit",
                "invalid_reasons": snapshot.invalid_reasons,
            }
            self.store.append_event(EventRecord(event_type="yield", timestamp=now, tick_id=tick_id, life_state=life_state.value, details=details))
            emit_log_line("yield", tick_id=tick_id, reason=reason, state=life_state.value, action="stop_turns_and_exit")
        elif life_state == LifeState.CRITICAL:
            distress_reason = "critical_life_state" if distress_injection is None else distress_injection["reason"]
            details = {
                "reason": distress_reason,
                "life_state": life_state.value,
                "instance_valid": True,
                "consecutive_failures": state.consecutive_failures,
                "action_taken": "normal_turns_disabled",
            }
            if distress_injection is not None:
                details["source"] = distress_injection["source"]
                if distress_injection.get("payload_parse_error"):
                    details["payload_parse_error"] = True
            self.store.append_event(EventRecord(event_type="distress", timestamp=now, tick_id=tick_id, life_state=life_state.value, details=details))
            emit_log_line("distress", tick_id=tick_id, reason=distress_reason, state=life_state.value, action="normal_turns_disabled")
        return TickResult(
            tick_id=tick_id,
            life_state=life_state,
            instance_valid=snapshot.instance_valid,
            heartbeat_age_sec=state.heartbeat_age_sec,
            consecutive_failures=state.consecutive_failures,
        )

    def run_turn(self, state: RuntimeState, *, next_heartbeat_at: datetime, now: datetime | None = None) -> TurnResult:
        """Run at most one work slice, but only when heartbeat safety allows it."""

        now = now or utc_now()
        turn_id = self.next_turn_id()
        self.store.append_event(EventRecord(event_type="turn_started", timestamp=now, turn_id=turn_id, life_state=state.life_state))
        remaining = (next_heartbeat_at - now).total_seconds()

        if remaining <= self.lifecycle.turn_guard_window_sec:
            details = {
                "reason": "heartbeat_deadline_near",
                "runtime_gate_context": build_runtime_gate_context(
                    state,
                    instance_valid=state.instance_valid,
                    critical_blocked=state.life_state == LifeState.CRITICAL.value,
                    conservative_mode=self._conservative_until_next_patrol,
                    seconds_to_heartbeat=remaining,
                ),
            }
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=True, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="heartbeat_deadline_near")
            return result
        snapshot = self.instance_guard.snapshot(now)
        if not snapshot.instance_valid:
            reason = snapshot.invalid_reasons[0] if snapshot.invalid_reasons else "instance_invalid"
            details = {
                "reason": reason,
                "runtime_gate_context": build_runtime_gate_context(
                    state,
                    instance_valid=False,
                    critical_blocked=False,
                    conservative_mode=self._conservative_until_next_patrol,
                    seconds_to_heartbeat=remaining,
                ),
            }
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason=reason)
            return result
        if state.life_state == LifeState.CRITICAL.value:
            details = {
                "reason": "critical_life_state",
                "runtime_gate_context": build_runtime_gate_context(
                    state,
                    instance_valid=True,
                    critical_blocked=True,
                    conservative_mode=self._conservative_until_next_patrol,
                    seconds_to_heartbeat=remaining,
                ),
            }
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="critical_life_state")
            return result
        if not self.pending_work:
            details = {
                "reason": "no_work",
                "runtime_gate_context": build_runtime_gate_context(
                    state,
                    instance_valid=True,
                    critical_blocked=False,
                    conservative_mode=self._conservative_until_next_patrol,
                    seconds_to_heartbeat=remaining,
                ),
            }
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="no_work")
            return result

        work_slice = self._pop_next_executable_work()
        if work_slice is None:
            details = {
                "reason": "conservative_mode_waiting_for_patrol",
                "runtime_gate_context": build_runtime_gate_context(
                    state,
                    instance_valid=True,
                    critical_blocked=False,
                    conservative_mode=self._conservative_until_next_patrol,
                    seconds_to_heartbeat=remaining,
                ),
            }
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line(
                "turn",
                turn_id=turn_id,
                state=state.life_state,
                executed=False,
                reason="conservative_mode_waiting_for_patrol",
            )
            return result

        details: dict[str, Any] = {
            "work_slice": work_slice.name,
            "work_kind": work_slice.kind,
            "status": "completed",
            "runtime_gate_context": build_runtime_gate_context(
                state,
                instance_valid=True,
                critical_blocked=False,
                conservative_mode=self._conservative_until_next_patrol,
                seconds_to_heartbeat=remaining,
            ),
        }
        if work_slice.kind == "patrol":
            # Round 1.H H-2c: publish the process-current trace context before patrol
            # so patrol-time owner hooks (e.g. drive_state.l2.approach_delta) share this
            # turn's turn_index. Only while tracing -> no-op + byte-equivalent when off.
            if self.trace_sink.enabled:
                set_current_trace(self.trace_sink, self._trace_turn_index)
            extra_shared_facts = (
                (self.extra_shared_facts_provider() or None)
                if self.extra_shared_facts_provider is not None
                else None
            )
            patrol_result = execute_patrol(
                work_slice.name,
                self.store,
                state,
                self.external_life,
                now,
                due_at=work_slice.due_at,
                sensor_registry=self.sensor_registry,
                extra_shared_facts=extra_shared_facts,
            )
            details.update(
                {
                    "cadence": patrol_result.cadence,
                    "overall_status": patrol_result.snapshot.overall_status,
                    "primary_gap": patrol_result.snapshot.primary_gap,
                    "pressure_count": patrol_result.pressure_count,
                    "opened_count": patrol_result.opened_count,
                    "resolved_count": patrol_result.resolved_count,
                    "signal_summary": patrol_result.signal_summary.to_dict(),
                    "signal_batch": patrol_result.signal_batch,
                    "signal_routing": patrol_result.routing_decision.to_dict(),
                    "drive_summary": patrol_result.drive_summary.to_dict(),
                    "drive_broadcast": patrol_result.drive_broadcast.to_dict(),
                }
            )
            prior_response_history = self.store.read_response_history()
            reflex_plan = build_protective_reflex(
                patrol_result.pressure_table,
                state,
                routing_decision=patrol_result.routing_decision,
            )
            if reflex_plan is not None:
                details["reflex"] = {
                    "response_mode": reflex_plan["response_mode"],
                    "pressure_id": reflex_plan["pressure_id"],
                    "pressure_type": reflex_plan["pressure_type"],
                    "pressure_reason": reflex_plan["pressure_reason"],
                    "life_state": reflex_plan["life_state"],
                }
            conservative_before_patrol = self._conservative_until_next_patrol
            if conservative_before_patrol:
                self._conservative_until_next_patrol = False
            response_summary = None
            deliberation_audit = None
            release_decision = None
            release_token = None
            selected_candidate_id = None
            habit_narrowed = False
            habit_narrowed_from = None
            if reflex_plan is not None:
                release_decision = reflex_plan["release_decision"]
                assert isinstance(release_decision, ReleaseDecision)
                release_token = release_decision.release_token
                selected_candidate_id = release_decision.selected_candidate_id
                details["execution_lane"] = "fast"
                details["reflex"]["release_authorized"] = release_token is not None
                details["reflex"]["selected_candidate_id"] = selected_candidate_id
                response_summary = maybe_respond_after_patrol(
                    self.store,
                    state,
                    now,
                    runtime=self,
                    allow_repair_side_effects=not conservative_before_patrol,
                    drive_context=patrol_result.drive_broadcast,
                    release_context=_release_context_with_observation(
                        release_decision.release_context, extra_shared_facts
                    ),
                    release_token=release_token,
                    selected_candidate_id=selected_candidate_id,
                )
            else:
                deliberation_input = build_deliberation_input_from_store(
                    self.store,
                    patrol_result.signal_batch,
                    patrol_result.drive_broadcast.to_dict(),
                    details["runtime_gate_context"],
                    patrol_result.pressure_table,
                    working_memory_backend=self.working_memory_backend,
                    llm_adapter=self.working_memory_adapter,
                    working_memory_advisory_source=self.working_memory_advisory_source,
                    response_history=prior_response_history,
                )
                deliberation_audit, memory_stub = run_deliberation(
                    now, deliberation_input, producer=self.candidate_producer
                )
                if self.trace_sink.enabled:
                    self._emit_p1a_seam_trace(
                        deliberation_input, deliberation_audit, extra_shared_facts, patrol_result.snapshot
                    )
                self.store.append_deliberation_audit(deliberation_audit.to_dict())
                if memory_stub is not None:
                    append_cognitive_memory_stub(self.store, memory_stub)
                release_decision = deliberation_audit.release_decision
                release_token = deliberation_audit.release_token
                learning_context = release_decision.get("learning_context") if isinstance(release_decision.get("learning_context"), dict) else {}
                selected_candidate_id = release_decision.get("selected_candidate_id")
                selected_candidate = next(
                    (
                        candidate
                        for candidate in deliberation_audit.candidates
                        if candidate.get("candidate_id") == selected_candidate_id
                    ),
                    None,
                )
                selected_parameter_domain = (
                    selected_candidate.get("parameter_domain")
                    if isinstance(selected_candidate, dict) and isinstance(selected_candidate.get("parameter_domain"), dict)
                    else {}
                )
                habit_narrowed = bool(learning_context.get("habit_narrowed", False))
                habit_narrowed_from = (
                    int(selected_parameter_domain.get("habit_narrowed_from", 0)) or None
                    if habit_narrowed
                    else None
                )
                details["execution_lane"] = "slow"
                details["deliberation"] = {
                    "outcome": release_decision.get("outcome"),
                    "selected_action": release_decision.get("selected_action"),
                    "selected_candidate_id": selected_candidate_id,
                    "habit_narrowed": habit_narrowed,
                    "habit_narrowed_from": habit_narrowed_from,
                    "release_authorized": release_token is not None,
                }
                release_context = deliberation_audit.release_decision.get("release_context")
                if (
                    response_summary is None
                    and deliberation_audit.release_decision.get("outcome") == "compatibility_release"
                    and isinstance(release_context, dict)
                    and release_context.get("bridge_target") == "pressure_led_compatibility"
                ):
                    response_summary = maybe_respond_after_patrol(
                        self.store,
                        state,
                        now,
                        runtime=self,
                        allow_repair_side_effects=not conservative_before_patrol,
                        drive_context=patrol_result.drive_broadcast,
                        release_context=_release_context_with_observation(
                            release_context, extra_shared_facts
                        ),
                        release_token=release_token,
                        selected_candidate_id=selected_candidate_id,
                    )
            if self.trace_sink.enabled and response_summary is not None:
                self._emit_bridge_resolve_action_trace(response_summary)
            details["runtime_gate_context"] = build_runtime_gate_context(
                state,
                instance_valid=True,
                critical_blocked=False,
                conservative_mode=self._conservative_until_next_patrol,
                seconds_to_heartbeat=max((next_heartbeat_at - now).total_seconds(), 0.0),
            )
            if response_summary is not None:
                response_history = self.store.read_response_history()
                latest_response_history = response_history[-1] if response_history else None
                release_record = deliberation_audit or {
                    "recorded_at": now.isoformat(),
                    "release_decision": release_decision.to_dict()
                    if isinstance(release_decision, ReleaseDecision)
                    else dict(release_decision or {}),
                }
                learning_outcome = build_learning_outcome_record(
                    now.isoformat(),
                    release_record,
                    response_summary,
                    latest_response_history,
                )
                append_learning_outcome(self.store, learning_outcome.to_dict())
                habit_bias_entries = [summary.to_dict() for summary in summarize_habit_bias(
                    read_learning_outcomes(self.store),
                    situation_key=learning_outcome.content["situation_key"],
                )]
                if habit_bias_entries:
                    append_habit_bias(self.store, habit_bias_entries[0])
                details["response"] = {
                    "pressure_id": response_summary["pressure_id"],
                    "pressure_type": response_summary["pressure_type"],
                    "selected_action": response_summary["selected_action"],
                    "habit_narrowed": habit_narrowed,
                    "habit_narrowed_from": habit_narrowed_from,
                }
                self.store.append_event(
                    EventRecord(
                        event_type="response_selected",
                        timestamp=now,
                        turn_id=turn_id,
                        life_state=state.life_state,
                        details=build_response_selected_event_details(
                            response_summary,
                            work_slice=work_slice.name,
                            work_kind=work_slice.kind,
                            selected_candidate_id=selected_candidate_id,
                            habit_narrowed=habit_narrowed,
                            habit_narrowed_from=habit_narrowed_from,
                        ),
                    )
                )

        # Round 1.H H-2c: close out this turn's trace context (only after a traced
        # patrol set it). Advance the shared turn_index and reset to the no-op sink so
        # later non-patrol slices don't emit. Gated on tracing -> byte-equivalent off.
        if self.trace_sink.enabled and work_slice.kind == "patrol":
            self._trace_turn_index += 1
            reset_current_trace()
        state.last_turn_id = turn_id
        state.updated_at = now
        self.store.write_runtime_state(state)
        self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
        emit_log_line(
            "turn",
            turn_id=turn_id,
            state=state.life_state,
            executed=True,
            work_slice=work_slice.name,
            work_kind=work_slice.kind,
            status="completed",
            cadence=details.get("cadence"),
            overall_status=details.get("overall_status"),
            pressure_count=details.get("pressure_count"),
        )
        return TurnResult(
            turn_id=turn_id,
            executed=True,
            yielded_to_heartbeat=False,
            work_slice=work_slice.name,
            work_kind=work_slice.kind,
            details=details,
        )
