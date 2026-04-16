"""Heartbeat-first lifecycle runtime that coordinates ticks, turns, and patrol work."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .config import ExternalLifeConfig, LifecycleConfig
from .instance import InstanceGuard, InstanceSnapshot
from .patrol import PatrolScheduler, execute_patrol
from .response import build_response_selected_event_details, maybe_respond_after_patrol
from .state import EventRecord, RuntimeState, StateStore, emit_log_line, utc_now


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


class LifecycleRuntime:
    """Run the heartbeat loop while preserving heartbeat priority over turn work."""

    def __init__(
        self,
        store: StateStore,
        instance_guard: InstanceGuard,
        lifecycle: LifecycleConfig,
        external_life: ExternalLifeConfig | None = None,
    ) -> None:
        self.store = store
        self.instance_guard = instance_guard
        self.lifecycle = lifecycle
        self.external_life = external_life or ExternalLifeConfig()
        self.patrol_scheduler = PatrolScheduler(self.external_life)
        self.pending_work: deque[WorkSlice] = deque([
            WorkSlice(name="self_check"),
            WorkSlice(name="persist_marker"),
        ])
        self._conservative_until_next_patrol = False
        self._tick_counter = 0
        self._turn_counter = 0

    def activate_conservative_until_next_patrol(self) -> None:
        """Pause ordinary turn work until one later patrol finishes."""

        self._conservative_until_next_patrol = True

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

        # Preserve heartbeat-first behavior by refusing turn work near the next deadline.
        if remaining <= self.lifecycle.turn_guard_window_sec:
            details = {"reason": "heartbeat_deadline_near"}
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=True, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="heartbeat_deadline_near")
            return result
        snapshot = self.instance_guard.snapshot(now)
        if not snapshot.instance_valid:
            reason = snapshot.invalid_reasons[0] if snapshot.invalid_reasons else "instance_invalid"
            details = {"reason": reason}
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason=reason)
            return result
        if state.life_state == LifeState.CRITICAL.value:
            details = {"reason": "critical_life_state"}
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="critical_life_state")
            return result
        if not self.pending_work:
            details = {"reason": "no_work"}
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details=details)
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="no_work")
            return result

        work_slice = self._pop_next_executable_work()
        if work_slice is None:
            details = {"reason": "conservative_mode_waiting_for_patrol"}
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
        }
        if work_slice.kind == "patrol":
            patrol_result = execute_patrol(
                work_slice.name,
                self.store,
                state,
                self.external_life,
                now,
                due_at=work_slice.due_at,
            )
            details.update(
                {
                    "cadence": patrol_result.cadence,
                    "overall_status": patrol_result.snapshot.overall_status,
                    "primary_gap": patrol_result.snapshot.primary_gap,
                    "pressure_count": patrol_result.pressure_count,
                    "opened_count": patrol_result.opened_count,
                    "resolved_count": patrol_result.resolved_count,
                }
            )
            conservative_before_patrol = self._conservative_until_next_patrol
            if conservative_before_patrol:
                self._conservative_until_next_patrol = False
            response_summary = maybe_respond_after_patrol(
                self.store,
                state,
                now,
                runtime=self,
                allow_repair_side_effects=not conservative_before_patrol,
            )
            if response_summary is not None:
                details["response"] = response_summary
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
                        ),
                    )
                )

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
