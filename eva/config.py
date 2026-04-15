from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvaPaths:
    runtime_dir: Path
    active_instance_file: Path
    runtime_state_file: Path
    events_file: Path
    lock_file: Path
    distress_injection_file: Path


@dataclass(frozen=True)
class LifecycleConfig:
    heartbeat_interval_sec: float = 15.0
    degraded_after_missed_beats: int = 3
    critical_after_missed_beats: int = 9
    lease_duration_sec: float = 20.0
    recovering_window_sec: float = 30.0
    turn_guard_window_sec: float = 0.5


@dataclass(frozen=True)
class LoopControl:
    max_ticks: int | None = None
    max_turns: int | None = None
    max_runtime_sec: float | None = None
    idle_sleep_sec: float = 0.05


@dataclass(frozen=True)
class RuntimeConfig:
    paths: EvaPaths
    lifecycle: LifecycleConfig = LifecycleConfig()
    control: LoopControl = LoopControl()


def build_runtime_paths(base_dir: str | Path) -> EvaPaths:
    runtime_dir = Path(base_dir).expanduser().resolve()
    return EvaPaths(
        runtime_dir=runtime_dir,
        active_instance_file=runtime_dir / "active_instance.json",
        runtime_state_file=runtime_dir / "runtime_state.json",
        events_file=runtime_dir / "events.jsonl",
        lock_file=runtime_dir / "eva.lock",
        distress_injection_file=runtime_dir / "distress_injection.json",
    )


def build_runtime_config(base_dir: str | Path, *, lifecycle: LifecycleConfig | None = None, control: LoopControl | None = None) -> RuntimeConfig:
    return RuntimeConfig(
        paths=build_runtime_paths(base_dir),
        lifecycle=lifecycle or LifecycleConfig(),
        control=control or LoopControl(),
    )
