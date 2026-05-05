"""Schedule patrol cadences and execute one patrol end to end."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..kernel import ActivePressureTable, DriveStateTable, ExternalLifeConfig, ExternalLifeSnapshot, RuntimeState, StateStore
from ..l2_drive.broadcast import DriveBroadcast, build_drive_broadcast
from ..l2_drive.drive_state import DriveSummary, update_drive_state
from ..l2_drive.pressure_to_drive import build_active_pressure_table
from .history import persist_patrol_artifacts
from .judgment import build_external_life_snapshot
from .routing import RoutingDecision, build_routing_decision
from .sensing import collect_external_life_inputs
from .sensor_registry import SensorRegistry
from .signal_bus import SignalRecord, SignalDispatchSummary, build_patrol_signal_artifacts

PATROL_ORDER = ("shallow", "deep", "full")
PATROL_INTERVAL_SECONDS = {
    "shallow": "shallow_patrol_interval_sec",
    "deep": "deep_patrol_interval_sec",
    "full": "full_report_interval_sec",
}


@dataclass(frozen=True)
class PatrolPlan:
    """One patrol cadence that has become due for execution."""

    name: str
    due_at: datetime


@dataclass
class PatrolResult:
    """Summary of one completed patrol run."""

    cadence: str
    snapshot: ExternalLifeSnapshot
    pressure_count: int
    opened_count: int
    resolved_count: int
    pressure_table: ActivePressureTable
    signals: list[SignalRecord]
    signal_summary: SignalDispatchSummary
    signal_batch: dict[str, object]
    routing_decision: RoutingDecision
    drive_state: DriveStateTable
    drive_summary: DriveSummary
    drive_broadcast: DriveBroadcast


class PatrolScheduler:
    """Track next due times for each patrol cadence."""

    def __init__(self, config: ExternalLifeConfig) -> None:
        self.config = config
        self._next_due_at: dict[str, datetime] = {}

    def due_patrols(self, now: datetime, queued_patrols: set[str]) -> list[PatrolPlan]:
        """Return patrols that are due now and not already queued."""

        due: list[PatrolPlan] = []
        for name in PATROL_ORDER:
            next_due_at = self._next_due_at.get(name)
            if next_due_at is None:
                self._next_due_at[name] = now + timedelta(seconds=self._interval_seconds(name))
                continue
            if now < next_due_at or name in queued_patrols:
                continue
            due.append(PatrolPlan(name=name, due_at=next_due_at))
            interval = timedelta(seconds=self._interval_seconds(name))

            # Advance until the next stored deadline moves beyond the current time.
            while next_due_at <= now:
                next_due_at += interval
            self._next_due_at[name] = next_due_at
        return due

    def _interval_seconds(self, name: str) -> float:
        """Read the configured interval for one patrol cadence."""

        return float(getattr(self.config, PATROL_INTERVAL_SECONDS[name]))


def execute_patrol(
    cadence: str,
    store: StateStore,
    runtime_state: RuntimeState,
    config: ExternalLifeConfig,
    now: datetime,
    *,
    due_at: datetime | None = None,
    sensor_registry: SensorRegistry | None = None,
) -> PatrolResult:
    """Run one patrol from sensing through persistence and history writing."""

    previous_snapshot = store.read_external_life_snapshot()
    inputs = collect_external_life_inputs(
        store,
        runtime_state,
        config,
        now,
        due_at=due_at,
        previous_snapshot=previous_snapshot,
        sensor_registry=sensor_registry,
    )
    snapshot = build_external_life_snapshot(
        cadence,
        inputs,
        config,
        now,
        previous_snapshot=previous_snapshot,
    )
    previous_pressures = store.read_active_pressures()
    pressure_table, opened_pressures, resolved_pressures = build_active_pressure_table(snapshot, previous_pressures)
    signals, signal_summary, signal_batch = build_patrol_signal_artifacts(snapshot, pressure_table)
    routing_decision = build_routing_decision(signals)
    previous_drive_state = store.read_drive_state()
    drive_state, drive_summary = update_drive_state(previous_drive_state, snapshot, signals)
    drive_broadcast = build_drive_broadcast(drive_state)
    store.write_drive_state(drive_state)
    persist_patrol_artifacts(
        store,
        snapshot,
        pressure_table,
        opened_pressures=opened_pressures,
        resolved_pressures=resolved_pressures,
        append_snapshot=cadence != "shallow",
    )
    return PatrolResult(
        cadence=cadence,
        snapshot=snapshot,
        pressure_count=len(pressure_table.pressures),
        opened_count=len(opened_pressures),
        resolved_count=len(resolved_pressures),
        pressure_table=pressure_table,
        signals=signals,
        signal_summary=signal_summary,
        signal_batch=signal_batch,
        routing_decision=routing_decision,
        drive_state=drive_state,
        drive_summary=drive_summary,
        drive_broadcast=drive_broadcast,
    )
