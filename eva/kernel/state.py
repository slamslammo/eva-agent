"""Persistence models and storage helpers for runtime state and append-only logs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import EvaPaths


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def to_iso8601(value: datetime | None) -> str | None:
    """Serialize a UTC datetime into the wire format used by runtime artifacts."""

    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def from_iso8601(value: str | None) -> datetime | None:
    """Parse an artifact timestamp back into a UTC datetime."""

    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _format_log_value(value: Any) -> str:
    """Normalize log field values into short single-line text output."""

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
    """Emit a compact structured log line for human and journal inspection."""

    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_format_log_value(value)}")
    print(" ".join(parts), flush=True)


@dataclass
class ActiveInstanceRecord:
    """Persisted ownership record for the currently active runtime instance."""

    instance_id: str
    generation: int
    lease_expires_at: datetime
    lock_holder: bool
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize the active-instance record for JSON storage."""

        return {
            "instance_id": self.instance_id,
            "generation": self.generation,
            "lease_expires_at": to_iso8601(self.lease_expires_at),
            "lock_holder": self.lock_holder,
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveInstanceRecord":
        """Deserialize an active-instance record from JSON payload data."""

        return cls(
            instance_id=payload["instance_id"],
            generation=int(payload["generation"]),
            lease_expires_at=from_iso8601(payload["lease_expires_at"]) or utc_now(),
            lock_holder=bool(payload.get("lock_holder", False)),
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class RuntimeState:
    """Persisted Step 0 life-loop state shared across ticks and turns."""

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
        """Serialize runtime state for atomic JSON persistence."""

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
        """Deserialize runtime state from the on-disk JSON payload."""

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
class DimensionSnapshot:
    """Judged status and evidence for one external-life dimension."""

    status: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize one judged dimension."""

        return {
            "status": self.status,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DimensionSnapshot":
        """Deserialize one judged dimension from artifact data."""

        return cls(
            status=str(payload.get("status", "healthy")),
            evidence=dict(payload.get("evidence", {})),
        )


@dataclass
class ExternalLifeSnapshot:
    """Current Step 1 view of external-life conditions and dominant gap."""

    captured_at: datetime
    source_patrol: str
    dimensions: dict[str, DimensionSnapshot]
    overall_status: str
    primary_gap: dict[str, Any] = field(default_factory=dict)
    trend: str = "unknown"
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize a full external-life snapshot for current-state storage."""

        return {
            "captured_at": to_iso8601(self.captured_at),
            "source_patrol": self.source_patrol,
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "overall_status": self.overall_status,
            "primary_gap": self.primary_gap,
            "trend": self.trend,
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExternalLifeSnapshot":
        """Deserialize a full external-life snapshot from JSON payload data."""

        raw_dimensions = payload.get("dimensions", {})
        return cls(
            captured_at=from_iso8601(payload.get("captured_at")) or utc_now(),
            source_patrol=str(payload.get("source_patrol", "shallow")),
            dimensions={
                key: DimensionSnapshot.from_dict(value)
                for key, value in raw_dimensions.items()
                if isinstance(value, dict)
            },
            overall_status=str(payload.get("overall_status", "healthy")),
            primary_gap=dict(payload.get("primary_gap", {})),
            trend=str(payload.get("trend", "unknown")),
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class ActivePressure:
    """One currently active survival pressure derived from a judged gap."""

    pressure_id: str
    type: str
    severity: str
    evidence: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    trend: str
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize one active pressure for current-state storage."""

        return {
            "pressure_id": self.pressure_id,
            "type": self.type,
            "severity": self.severity,
            "evidence": self.evidence,
            "first_seen_at": to_iso8601(self.first_seen_at),
            "last_seen_at": to_iso8601(self.last_seen_at),
            "trend": self.trend,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActivePressure":
        """Deserialize one active pressure from JSON payload data."""

        now = utc_now()
        return cls(
            pressure_id=str(payload["pressure_id"]),
            type=str(payload.get("type", "continuity")),
            severity=str(payload.get("severity", "degraded")),
            evidence=dict(payload.get("evidence", {})),
            first_seen_at=from_iso8601(payload.get("first_seen_at")) or now,
            last_seen_at=from_iso8601(payload.get("last_seen_at")) or now,
            trend=str(payload.get("trend", "unknown")),
            active=bool(payload.get("active", True)),
        )


@dataclass
class ActivePressureTable:
    """Current table of active pressures derived from the latest patrol."""

    captured_at: datetime
    pressures: list[ActivePressure] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the active-pressure table for current-state storage."""

        return {
            "captured_at": to_iso8601(self.captured_at),
            "pressures": [pressure.to_dict() for pressure in self.pressures],
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActivePressureTable":
        """Deserialize the active-pressure table from JSON payload data."""

        return cls(
            captured_at=from_iso8601(payload.get("captured_at")) or utc_now(),
            pressures=[
                ActivePressure.from_dict(item)
                for item in payload.get("pressures", [])
                if isinstance(item, dict)
            ],
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class DriveState:
    """One continuous L2 drive value and its latest local update summary."""

    drive_type: str
    level: float = 0.0
    delta: float = 0.0
    trend: str = "unknown"
    contributors: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize one continuous drive record for current-state storage."""

        return {
            "drive_type": self.drive_type,
            "level": self.level,
            "delta": self.delta,
            "trend": self.trend,
            "contributors": list(self.contributors),
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DriveState":
        """Deserialize one continuous drive record from JSON payload data."""

        return cls(
            drive_type=str(payload.get("drive_type", "survival")),
            level=float(payload.get("level", 0.0)),
            delta=float(payload.get("delta", 0.0)),
            trend=str(payload.get("trend", "unknown")),
            contributors=[str(item) for item in payload.get("contributors", [])],
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class DriveStateTable:
    """Current table of continuous L2 drives derived from patrol updates."""

    captured_at: datetime
    drives: list[DriveState] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the continuous drive table for current-state storage."""

        return {
            "captured_at": to_iso8601(self.captured_at),
            "drives": [drive.to_dict() for drive in self.drives],
            "updated_at": to_iso8601(self.updated_at),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DriveStateTable":
        """Deserialize the continuous drive table from JSON payload data."""

        return cls(
            captured_at=from_iso8601(payload.get("captured_at")) or utc_now(),
            drives=[
                DriveState.from_dict(item)
                for item in payload.get("drives", [])
                if isinstance(item, dict)
            ],
            updated_at=from_iso8601(payload.get("updated_at")) or utc_now(),
        )


@dataclass
class EventRecord:
    """Append-only structured event written into events.jsonl."""

    event_type: str
    timestamp: datetime
    instance_id: str | None = None
    generation: int | None = None
    life_state: str | None = None
    tick_id: str | None = None
    turn_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize an event record and omit optional empty fields."""

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
    """Read and write runtime artifacts with atomic current-state updates."""

    def __init__(self, paths: EvaPaths, *, append_only_rotation_max_bytes: int | None = None) -> None:
        self.paths = paths
        self.append_only_rotation_max_bytes = append_only_rotation_max_bytes

    def ensure_runtime_dir(self) -> None:
        """Create the runtime directory if it does not exist yet."""

        self.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.paths.append_only_archive_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_json(self, file_path: Path, payload: dict[str, Any]) -> None:
        """Write a JSON artifact through a temp file and atomic replace."""

        self.ensure_runtime_dir()
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(file_path)

    def _append_jsonl(self, file_path: Path, payload: dict[str, Any]) -> None:
        """Append one JSON object to an append-only log file."""

        self.ensure_runtime_dir()
        encoded_line = json.dumps(payload, ensure_ascii=False) + "\n"
        if self.append_only_rotation_max_bytes is not None and file_path.exists():
            current_size = file_path.stat().st_size
            if current_size > 0 and current_size + len(encoded_line.encode("utf-8")) > self.append_only_rotation_max_bytes:
                self._rotate_append_only_file(file_path)
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(encoded_line)
            handle.flush()

    def _rotate_append_only_file(self, file_path: Path) -> None:
        """Seal one live append-only file into the archive directory and reopen the live path."""

        self.ensure_runtime_dir()
        if not file_path.exists() or file_path.stat().st_size == 0:
            return
        archive_path = self._next_archive_path_for(file_path)
        file_path.replace(archive_path)

    def _next_archive_path_for(self, file_path: Path) -> Path:
        """Return the next deterministic archived segment path for one live append-only file."""

        stem = file_path.stem
        suffix = file_path.suffix
        timestamp = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
        candidate = self.paths.append_only_archive_dir / f"{stem}.{timestamp}{suffix}"
        counter = 1
        while candidate.exists():
            candidate = self.paths.append_only_archive_dir / f"{stem}.{timestamp}.{counter}{suffix}"
            counter += 1
        return candidate

    def _read_jsonl_history(self, file_path: Path) -> list[dict[str, Any]]:
        """Read archived segments plus the live file as one ordered logical history."""

        lines: list[str] = []
        lines.extend(self._read_archived_jsonl_lines(file_path))
        if file_path.exists():
            lines.extend(file_path.read_text(encoding="utf-8").splitlines())
        return [json.loads(line) for line in lines if line.strip()]

    def _read_archived_jsonl_lines(self, file_path: Path) -> list[str]:
        """Read all archived segment lines for one append-only live path in order."""

        archive_prefix = f"{file_path.stem}."
        archive_suffix = file_path.suffix
        archived_paths = sorted(
            (
                path
                for path in self.paths.append_only_archive_dir.glob(f"{file_path.stem}.*{file_path.suffix}")
                if path.is_file() and path.name.startswith(archive_prefix) and path.name.endswith(archive_suffix)
            ),
            key=lambda path: self._archived_segment_sort_key(file_path, path),
        )
        lines: list[str] = []
        for archived_path in archived_paths:
            lines.extend(archived_path.read_text(encoding="utf-8").splitlines())
        return lines

    def _archived_segment_sort_key(self, live_file_path: Path, archived_path: Path) -> tuple[str, int, str]:
        """Return a stable ordering key for archived append-only segments."""

        archive_suffix = live_file_path.suffix
        archive_prefix = f"{live_file_path.stem}."
        archive_name = archived_path.name
        if archive_suffix:
            archive_name = archive_name[: -len(archive_suffix)]
        remainder = archive_name[len(archive_prefix):]
        timestamp, separator, counter_text = remainder.partition(".")
        if not separator:
            return timestamp, 0, archived_path.name
        try:
            return timestamp, int(counter_text), archived_path.name
        except ValueError:
            return timestamp, 0, archived_path.name

    def write_active_instance(self, record: ActiveInstanceRecord) -> None:
        """Persist the active-instance record."""

        self._atomic_write_json(self.paths.active_instance_file, record.to_dict())

    def read_active_instance(self) -> ActiveInstanceRecord | None:
        """Read the active-instance record if it exists."""

        if not self.paths.active_instance_file.exists():
            return None
        payload = json.loads(self.paths.active_instance_file.read_text(encoding="utf-8"))
        return ActiveInstanceRecord.from_dict(payload)

    def write_runtime_state(self, state: RuntimeState) -> None:
        """Persist the current Step 0 runtime state."""

        self._atomic_write_json(self.paths.runtime_state_file, state.to_dict())

    def read_runtime_state(self) -> RuntimeState:
        """Read the current Step 0 runtime state or return defaults."""

        if not self.paths.runtime_state_file.exists():
            return RuntimeState()
        payload = json.loads(self.paths.runtime_state_file.read_text(encoding="utf-8"))
        return RuntimeState.from_dict(payload)

    def write_external_life_snapshot(self, snapshot: ExternalLifeSnapshot) -> None:
        """Persist the latest Step 1 external-life snapshot."""

        self._atomic_write_json(self.paths.external_life_snapshot_file, snapshot.to_dict())

    def read_external_life_snapshot(self) -> ExternalLifeSnapshot | None:
        """Read the latest Step 1 external-life snapshot if it exists."""

        if not self.paths.external_life_snapshot_file.exists():
            return None
        payload = json.loads(self.paths.external_life_snapshot_file.read_text(encoding="utf-8"))
        return ExternalLifeSnapshot.from_dict(payload)

    def write_active_pressures(self, table: ActivePressureTable) -> None:
        """Persist the latest active-pressure table."""

        self._atomic_write_json(self.paths.active_pressures_file, table.to_dict())

    def read_active_pressures(self) -> ActivePressureTable:
        """Read the latest active-pressure table or return an empty one."""

        if not self.paths.active_pressures_file.exists():
            return ActivePressureTable(captured_at=utc_now())
        payload = json.loads(self.paths.active_pressures_file.read_text(encoding="utf-8"))
        return ActivePressureTable.from_dict(payload)

    def write_drive_state(self, table: DriveStateTable) -> None:
        """Persist the latest continuous drive-state table."""

        self._atomic_write_json(self.paths.drive_state_file, table.to_dict())

    def read_drive_state(self) -> DriveStateTable | None:
        """Read the latest continuous drive-state table if it exists."""

        if not self.paths.drive_state_file.exists():
            return None
        payload = json.loads(self.paths.drive_state_file.read_text(encoding="utf-8"))
        return DriveStateTable.from_dict(payload)

    def append_survival_log(self, payload: dict[str, Any]) -> None:
        """Append one Step 1 history entry to survival_log.jsonl."""

        self._append_jsonl(self.paths.survival_log_file, payload)

    def read_survival_log(self) -> list[dict[str, Any]]:
        """Read the append-only survival history log."""

        return self._read_jsonl_history(self.paths.survival_log_file)

    def append_response_history(self, payload: dict[str, Any]) -> None:
        """Append one Step 2 response entry to response_history.jsonl."""

        self._append_jsonl(self.paths.response_history_file, payload)

    def read_response_history(self) -> list[dict[str, Any]]:
        """Read the append-only Step 2 response history log."""

        return self._read_jsonl_history(self.paths.response_history_file)

    def append_deliberation_audit(self, payload: dict[str, Any]) -> None:
        """Append one Phase B deliberation audit record."""

        self._append_jsonl(self.paths.deliberation_audit_file, payload)

    def read_deliberation_audit(self) -> list[dict[str, Any]]:
        """Read the append-only Phase B deliberation audit log."""

        return self._read_jsonl_history(self.paths.deliberation_audit_file)

    def append_llm_advisory_audit(self, payload: dict[str, Any]) -> None:
        """Append one Stage E LLM advisory audit record."""

        self._append_jsonl(self.paths.llm_advisory_audit_file, payload)

    def read_llm_advisory_audit(self) -> list[dict[str, Any]]:
        """Read the append-only Stage E LLM advisory audit log."""

        return self._read_jsonl_history(self.paths.llm_advisory_audit_file)

    def append_cognitive_memory_stub(self, payload: dict[str, Any]) -> None:
        """Append one minimal cognitive-memory stub entry."""

        self._append_jsonl(self.paths.cognitive_memory_stub_file, payload)

    def read_cognitive_memory_stub(self) -> list[dict[str, Any]]:
        """Read the append-only cognitive-memory stub log."""

        return self._read_jsonl_history(self.paths.cognitive_memory_stub_file)

    def append_learning_outcome(self, payload: dict[str, Any]) -> None:
        """Append one Phase C learning outcome record."""

        self._append_jsonl(self.paths.learning_outcomes_file, payload)

    def read_learning_outcomes(self) -> list[dict[str, Any]]:
        """Read the append-only Phase C learning outcome log."""

        return self._read_jsonl_history(self.paths.learning_outcomes_file)

    def append_habit_bias(self, payload: dict[str, Any]) -> None:
        """Append one Phase C habit-bias summary record."""

        self._append_jsonl(self.paths.habit_bias_file, payload)

    def read_habit_bias(self) -> list[dict[str, Any]]:
        """Read the append-only Phase C habit-bias log."""

        return self._read_jsonl_history(self.paths.habit_bias_file)

    def append_semantic_memory(self, payload: dict[str, Any]) -> None:
        """Append one Stage I semantic-memory record."""

        self._append_jsonl(self.paths.semantic_memory_file, payload)

    def read_semantic_memory(self) -> list[dict[str, Any]]:
        """Read the append-only Stage I semantic-memory log."""

        return self._read_jsonl_history(self.paths.semantic_memory_file)

    def append_event(self, event: EventRecord) -> None:
        """Append one lifecycle event to events.jsonl."""

        self._append_jsonl(self.paths.events_file, event.to_dict())

    def read_events(self) -> list[dict[str, Any]]:
        """Read the append-only lifecycle event log."""

        return self._read_jsonl_history(self.paths.events_file)
