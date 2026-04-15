from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .config import LifecycleConfig
from .instance import InstanceGuard, InstanceSnapshot
from .state import EventRecord, RuntimeState, StateStore, emit_log_line, utc_now


class LifeState(str, Enum):
    RECOVERING = "RECOVERING"
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class TickResult:
    tick_id: str
    life_state: LifeState
    instance_valid: bool
    heartbeat_age_sec: float
    consecutive_failures: int


@dataclass
class TurnResult:
    turn_id: str
    executed: bool
    yielded_to_heartbeat: bool
    work_slice: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class LifecycleRuntime:
    def __init__(self, store: StateStore, instance_guard: InstanceGuard, lifecycle: LifecycleConfig) -> None:
        self.store = store
        self.instance_guard = instance_guard
        self.lifecycle = lifecycle
        self.pending_work: deque[str] = deque(["self_check", "persist_marker"])
        self._tick_counter = 0
        self._turn_counter = 0

    def has_pending_work(self) -> bool:
        return bool(self.pending_work)

    def next_tick_id(self) -> str:
        self._tick_counter += 1
        return f"tick-{self._tick_counter:04d}"

    def next_turn_id(self) -> str:
        self._turn_counter += 1
        return f"turn-{self._turn_counter:04d}"

    def consume_distress_injection(self) -> dict[str, Any] | None:
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
        now = now or utc_now()
        turn_id = self.next_turn_id()
        self.store.append_event(EventRecord(event_type="turn_started", timestamp=now, turn_id=turn_id, life_state=state.life_state))
        remaining = (next_heartbeat_at - now).total_seconds()
        if remaining <= self.lifecycle.turn_guard_window_sec:
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=True, details={"reason": "heartbeat_deadline_near"})
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=result.details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="heartbeat_deadline_near")
            return result
        snapshot = self.instance_guard.snapshot(now)
        if not snapshot.instance_valid:
            reason = snapshot.invalid_reasons[0] if snapshot.invalid_reasons else "instance_invalid"
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details={"reason": reason})
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=result.details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason=reason)
            return result
        if state.life_state == LifeState.CRITICAL.value:
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details={"reason": "critical_life_state"})
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=result.details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="critical_life_state")
            return result
        if not self.pending_work:
            result = TurnResult(turn_id=turn_id, executed=False, yielded_to_heartbeat=False, details={"reason": "no_work"})
            self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details=result.details))
            emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=False, reason="no_work")
            return result
        work_slice = self.pending_work.popleft()
        result = TurnResult(turn_id=turn_id, executed=True, yielded_to_heartbeat=False, work_slice=work_slice, details={"status": "completed"})
        state.last_turn_id = turn_id
        state.updated_at = now
        self.store.write_runtime_state(state)
        self.store.append_event(EventRecord(event_type="turn_completed", timestamp=now, turn_id=turn_id, life_state=state.life_state, details={"work_slice": work_slice, "status": "completed"}))
        emit_log_line("turn", turn_id=turn_id, state=state.life_state, executed=True, work_slice=work_slice, status="completed")
        return result
