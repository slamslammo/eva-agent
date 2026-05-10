"""Configuration objects and path builders for eva-agent runtime files and cadences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvaPaths:
    """Resolved paths for runtime state, logs, and control files."""

    runtime_dir: Path
    append_only_archive_dir: Path
    active_instance_file: Path
    runtime_state_file: Path
    external_life_snapshot_file: Path
    drive_state_file: Path
    active_pressures_file: Path
    survival_log_file: Path
    response_history_file: Path
    deliberation_audit_file: Path
    llm_advisory_audit_file: Path
    cognitive_memory_stub_file: Path
    learning_outcomes_file: Path
    habit_bias_file: Path
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
class AppendOnlyArtifactsConfig:
    """Optional rotation/archive settings for append-only runtime tracks."""

    rotation_max_bytes: int | None = None
    archive_dir_name: str = "archive"


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
    append_only_artifacts: AppendOnlyArtifactsConfig = AppendOnlyArtifactsConfig()
    control: LoopControl = LoopControl()
    working_memory_backend: str = "local_rule_based"
    working_memory_adapter: Any | None = None
    working_memory_adapter_mode: str = "inert"
    working_memory_model_client_mode: str = "anthropic"
    working_memory_model_client_config: Any | None = None


def build_runtime_paths(
    base_dir: str | Path,
    *,
    archive_dir_name: str = "archive",
) -> EvaPaths:
    """Resolve all runtime artifact paths under the given base directory."""

    runtime_dir = Path(base_dir).expanduser().resolve()
    return EvaPaths(
        runtime_dir=runtime_dir,
        append_only_archive_dir=runtime_dir / archive_dir_name,
        active_instance_file=runtime_dir / "active_instance.json",
        runtime_state_file=runtime_dir / "runtime_state.json",
        external_life_snapshot_file=runtime_dir / "external_life_snapshot.json",
        drive_state_file=runtime_dir / "drive_state.json",
        active_pressures_file=runtime_dir / "active_pressures.json",
        survival_log_file=runtime_dir / "survival_log.jsonl",
        response_history_file=runtime_dir / "response_history.jsonl",
        deliberation_audit_file=runtime_dir / "deliberation_audit.jsonl",
        llm_advisory_audit_file=runtime_dir / "llm_advisory_audit.jsonl",
        cognitive_memory_stub_file=runtime_dir / "cognitive_memory_stub.jsonl",
        learning_outcomes_file=runtime_dir / "learning_outcomes.jsonl",
        habit_bias_file=runtime_dir / "habit_bias.jsonl",
        events_file=runtime_dir / "events.jsonl",
        lock_file=runtime_dir / "eva.lock",
        distress_injection_file=runtime_dir / "distress_injection.json",
    )


def build_runtime_config(
    base_dir: str | Path,
    *,
    lifecycle: LifecycleConfig | None = None,
    external_life: ExternalLifeConfig | None = None,
    append_only_artifacts: AppendOnlyArtifactsConfig | None = None,
    control: LoopControl | None = None,
    working_memory_backend: str = "local_rule_based",
    working_memory_adapter: Any | None = None,
    working_memory_adapter_mode: str = "inert",
    working_memory_model_client_mode: str = "anthropic",
    working_memory_model_client_config: Any | None = None,
) -> RuntimeConfig:
    """Build a runtime config and fill in omitted sections with defaults."""

    if working_memory_model_client_config is None:
        from eva.l3_deliberation.memory import WorkingMemoryModelClientConfig

        working_memory_model_client_config = WorkingMemoryModelClientConfig()

    append_only_config = append_only_artifacts or AppendOnlyArtifactsConfig()

    return RuntimeConfig(
        paths=build_runtime_paths(base_dir, archive_dir_name=append_only_config.archive_dir_name),
        lifecycle=lifecycle or LifecycleConfig(),
        external_life=external_life or ExternalLifeConfig(),
        append_only_artifacts=append_only_config,
        control=control or LoopControl(),
        working_memory_backend=working_memory_backend,
        working_memory_adapter=working_memory_adapter,
        working_memory_adapter_mode=working_memory_adapter_mode,
        working_memory_model_client_mode=working_memory_model_client_mode,
        working_memory_model_client_config=working_memory_model_client_config,
    )
