from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import EvaPaths


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso8601(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def from_iso8601(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _format_log_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return to_iso8601(value) or "null"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") or "0"
    if value is None:
        return "null"
    return str(value)


def emit_log_line(event: str, **fields: Any) -> None:
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_log_value(value)}")
    print(" ".join(parts), flush=True)


@dataclass
class ActiveInstanceRecord:
    instance_id: str
    generation: int
    lease_expires_at: datetime
    lock_holder: bool
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "generation": self.generation,
            "lease_expires_at": to_iso8601(self.lease_expires_at),
            "lock_holder": self.lock_holder,
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveInstanceRecord":
        return cls(
            instance_id=payload["instance_id"],
            generation=int(payload["generation"]),
            lease_expires_at=from_iso8601(payload["lease_expires_at"]) or utc_now(),
            lock_holder=bool(payload.get("lock_holder", False)),
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class RuntimeState:
    life_state: str = "RECOVERING"
    last_heartbeat_at: datetime | None = None
    last_tick_id: str | None = None
    last_turn_id: str | None = None
    heartbeat_age_sec: float = 0.0
    heartbeat_ok: bool = False
    state_io_ok: bool = True
    tick_ok: bool = False
    consecutive_failures: int = 0
    instance_valid: bool = False
    recovering_until: datetime | None = None
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "life_state": self.life_state,
            "last_heartbeat_at": to_iso8601(self.last_heartbeat_at),
            "last_tick_id": self.last_tick_id,
            "last_turn_id": self.last_turn_id,
            "heartbeat_age_sec": self.heartbeat_age_sec,
            "heartbeat_ok": self.heartbeat_ok,
            "state_io_ok": self.state_io_ok,
            "tick_ok": self.tick_ok,
            "consecutive_failures": self.consecutive_failures,
            "instance_valid": self.instance_valid,
            "recovering_until": to_iso8601(self.recovering_until),
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeState":
        return cls(
            life_state=payload.get("life_state", "RECOVERING"),
            last_heartbeat_at=from_iso8601(payload.get("last_heartbeat_at")),
            last_tick_id=payload.get("last_tick_id"),
            last_turn_id=payload.get("last_turn_id"),
            heartbeat_age_sec=float(payload.get("heartbeat_age_sec", 0.0)),
            heartbeat_ok=bool(payload.get("heartbeat_ok", False)),
            state_io_ok=bool(payload.get("state_io_ok", True)),
            tick_ok=bool(payload.get("tick_ok", False)),
            consecutive_failures=int(payload.get("consecutive_failures", 0)),
            instance_valid=bool(payload.get("instance_valid", False)),
            recovering_until=from_iso8601(payload.get("recovering_until")),
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class EventRecord:
    event_type: str
    timestamp: datetime
    instance_id: str | None = None
    generation: int | None = None
    life_state: str | None = None
    tick_id: str | None = None
    turn_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "event_type": self.event_type,
            "timestamp": to_iso8601(self.timestamp),
            "details": self.details,
        }
        if self.instance_id is not None:
            payload["instance_id"] = self.instance_id
        if self.generation is not None:
            payload["generation"] = self.generation
        if self.life_state is not None:
            payload["life_state"] = self.life_state
        if self.tick_id is not None:
            payload["tick_id"] = self.tick_id
        if self.turn_id is not None:
            payload["turn_id"] = self.turn_id
        return payload


class StateStore:
    def __init__(self, paths: EvaPaths) -> None:
        self.paths = paths

    def ensure_runtime_dir(self) -> None:
        self.paths.runtime_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_json(self, file_path: Path, payload: dict[str, Any]) -> None:
        self.ensure_runtime_dir()
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(file_path)

    def write_active_instance(self, record: ActiveInstanceRecord) -> None:
        self._atomic_write_json(self.paths.active_instance_file, record.to_dict())

    def read_active_instance(self) -> ActiveInstanceRecord | None:
        if not self.paths.active_instance_file.exists():
            return None
        payload = json.loads(self.paths.active_instance_file.read_text(encoding="utf-8"))
        return ActiveInstanceRecord.from_dict(payload)

    def write_runtime_state(self, state: RuntimeState) -> None:
        self._atomic_write_json(self.paths.runtime_state_file, state.to_dict())

    def read_runtime_state(self) -> RuntimeState:
        if not self.paths.runtime_state_file.exists():
            return RuntimeState()
        payload = json.loads(self.paths.runtime_state_file.read_text(encoding="utf-8"))
        return RuntimeState.from_dict(payload)

    def append_event(self, event: EventRecord) -> None:
        self.ensure_runtime_dir()
        with self.paths.events_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            handle.flush()

    def read_events(self) -> list[dict[str, Any]]:
        if not self.paths.events_file.exists():
            return []
        lines = self.paths.events_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
