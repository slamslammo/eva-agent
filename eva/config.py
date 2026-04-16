"""Configuration objects and path builders for eva-agent runtime files and cadences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaPaths:
    """Resolved paths for runtime state, logs, and control files."""

    runtime_dir: Path
    active_instance_file: Path
    runtime_state_file: Path
    external_life_snapshot_file: Path
    active_pressures_file: Path
    survival_log_file: Path
    response_history_file: Path
    events_file: Path
    lock_file: Path
    distress_injection_file: Path


@dataclass(frozen=True)
class LifecycleConfig:
    """Timing and safety thresholds for the heartbeat-first life loop."""

    heartbeat_interval_sec: float = 15.0
    degraded_after_missed_beats: int = 3
    critical_after_missed_beats: int = 9
    lease_duration_sec: float = 20.0
    recovering_window_sec: float = 30.0
    turn_guard_window_sec: float = 0.5


@dataclass(frozen=True)
class ExternalLifeConfig:
    """Cadence and threshold settings for Step 1 external life patrols."""

    shallow_patrol_interval_sec: float = 300.0
    deep_patrol_interval_sec: float = 1800.0
    full_report_interval_sec: float = 86400.0
    recent_event_window_sec: float = 1800.0
    disk_degraded_free_bytes: int = 2 * 1024 * 1024 * 1024
    disk_critical_free_bytes: int = 512 * 1024 * 1024
    continuity_restart_degraded_count: int = 2
    continuity_restart_critical_count: int = 4
    anomaly_degraded_count: int = 2
    anomaly_critical_count: int = 5


@dataclass(frozen=True)
class LoopControl:
    """Optional bounds for local runs, tests, and bounded verification."""

    max_ticks: int | None = None
    max_turns: int | None = None
    max_runtime_sec: float | None = None
    idle_sleep_sec: float = 0.05


@dataclass(frozen=True)
class RuntimeConfig:
    """Full runtime configuration passed into the main loop."""

    paths: EvaPaths
    lifecycle: LifecycleConfig = LifecycleConfig()
    external_life: ExternalLifeConfig = ExternalLifeConfig()
    control: LoopControl = LoopControl()


def build_runtime_paths(base_dir: str | Path) -> EvaPaths:
    """Resolve all runtime artifact paths under the given base directory."""

    runtime_dir = Path(base_dir).expanduser().resolve()
    return EvaPaths(
        runtime_dir=runtime_dir,
        active_instance_file=runtime_dir / "active_instance.json",
        runtime_state_file=runtime_dir / "runtime_state.json",
        external_life_snapshot_file=runtime_dir / "external_life_snapshot.json",
        active_pressures_file=runtime_dir / "active_pressures.json",
        survival_log_file=runtime_dir / "survival_log.jsonl",
        response_history_file=runtime_dir / "response_history.jsonl",
        events_file=runtime_dir / "events.jsonl",
        lock_file=runtime_dir / "eva.lock",
        distress_injection_file=runtime_dir / "distress_injection.json",
    )


def build_runtime_config(
    base_dir: str | Path,
    *,
    lifecycle: LifecycleConfig | None = None,
    external_life: ExternalLifeConfig | None = None,
    control: LoopControl | None = None,
) -> RuntimeConfig:
    """Build a runtime config and fill in omitted sections with defaults."""

    return RuntimeConfig(
        paths=build_runtime_paths(base_dir),
        lifecycle=lifecycle or LifecycleConfig(),
        external_life=external_life or ExternalLifeConfig(),
        control=control or LoopControl(),
    )
