from __future__ import annotations

import fcntl
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .config import LifecycleConfig
from .state import ActiveInstanceRecord, StateStore, utc_now


@dataclass(frozen=True)
class InstanceSnapshot:
    instance_id: str
    generation: int
    lock_held: bool
    lease_expires_at: datetime
    generation_matches: bool
    lease_not_expired: bool

    @property
    def invalid_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not self.lock_held:
            reasons.append("lock_lost")
        if not self.generation_matches:
            reasons.append("generation_mismatch")
        if not self.lease_not_expired:
            reasons.append("lease_expired")
        return reasons

    @property
    def instance_valid(self) -> bool:
        return self.lock_held and self.generation_matches and self.lease_not_expired


class InstanceGuard:
    def __init__(self, lock_file: Path, store: StateStore, lifecycle: LifecycleConfig) -> None:
        self.lock_file = lock_file
        self.store = store
        self.lifecycle = lifecycle
        self._lock_handle = None
        self.instance_id: str | None = None
        self.generation: int | None = None

    def acquire(self) -> None:
        self.store.ensure_runtime_dir()
        self._lock_handle = self.lock_file.open("a+", encoding="utf-8")
        fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self) -> None:
        if self._lock_handle is None:
            return
        fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
        self._lock_handle.close()
        self._lock_handle = None

    def start_instance(self, instance_id: str) -> ActiveInstanceRecord:
        current = self.store.read_active_instance()
        generation = 1 if current is None else current.generation + 1
        now = utc_now()
        lease_expires_at = now + timedelta(seconds=self.lifecycle.lease_duration_sec)
        record = ActiveInstanceRecord(
            instance_id=instance_id,
            generation=generation,
            lease_expires_at=lease_expires_at,
            lock_holder=True,
            updated_at=now,
        )
        self.store.write_active_instance(record)
        self.instance_id = instance_id
        self.generation = generation
        return record

    def refresh_lease(self) -> ActiveInstanceRecord:
        if self.instance_id is None or self.generation is None:
            raise RuntimeError("instance not started")
        now = utc_now()
        record = ActiveInstanceRecord(
            instance_id=self.instance_id,
            generation=self.generation,
            lease_expires_at=now + timedelta(seconds=self.lifecycle.lease_duration_sec),
            lock_holder=self.lock_held,
            updated_at=now,
        )
        self.store.write_active_instance(record)
        return record

    @property
    def lock_held(self) -> bool:
        return self._lock_handle is not None and not self._lock_handle.closed

    def snapshot(self, now: datetime | None = None) -> InstanceSnapshot:
        if self.instance_id is None or self.generation is None:
            raise RuntimeError("instance not started")
        now = now or utc_now()
        active = self.store.read_active_instance()
        generation_matches = active is not None and active.generation == self.generation and active.instance_id == self.instance_id
        lease_expires_at = active.lease_expires_at if active is not None else now
        lease_not_expired = active is not None and active.lease_expires_at >= now
        return InstanceSnapshot(
            instance_id=self.instance_id,
            generation=self.generation,
            lock_held=self.lock_held,
            lease_expires_at=lease_expires_at,
            generation_matches=generation_matches,
            lease_not_expired=lease_not_expired,
        )
