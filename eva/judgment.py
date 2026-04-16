"""Turn sensed external-life inputs into deterministic health judgments."""

from __future__ import annotations

from .config import ExternalLifeConfig
from .state import DimensionSnapshot, ExternalLifeSnapshot

SEVERITY_ORDER = {"healthy": 0, "degraded": 1, "critical": 2}
DIMENSION_PRIORITY = [
    "runtime_integrity",
    "host_continuity",
    "resource_state",
    "anomaly_accumulation",
]


def _host_continuity_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    """Judge whether host continuity still looks stable from restart signals."""

    restart_count = int(inputs.get("recent_restart_count", 0))
    status = "healthy"
    reason = "host_continuity_ok"
    if restart_count >= config.continuity_restart_critical_count:
        status = "critical"
        reason = "restart_flapping"
    elif restart_count >= config.continuity_restart_degraded_count:
        status = "degraded"
        reason = "restart_unstable"
    evidence = dict(inputs)
    evidence["reason"] = reason
    return DimensionSnapshot(status=status, evidence=evidence)


def _runtime_integrity_snapshot(inputs: dict[str, object]) -> DimensionSnapshot:
    """Judge whether the runtime still has the minimum files and legitimacy to act."""

    required_present = all(
        bool(inputs.get(key))
        for key in ("active_instance_present", "runtime_state_present", "events_present", "lock_present")
    )
    runtime_writable = bool(inputs.get("runtime_writable"))
    instance_valid = bool(inputs.get("instance_valid"))
    distress_count = int(inputs.get("recent_distress_count", 0))
    yield_count = int(inputs.get("recent_yield_count", 0))
    status = "healthy"
    reason = "runtime_integrity_ok"
    if not required_present:
        status = "critical"
        reason = "runtime_files_missing"
    elif not runtime_writable:
        status = "critical"
        reason = "runtime_not_writable"
    elif not instance_valid:
        status = "critical"
        reason = "instance_invalid"
    elif distress_count > 0:
        status = "critical"
        reason = "recent_distress_detected"
    elif yield_count > 0:
        status = "degraded"
        reason = "recent_yield_detected"
    evidence = dict(inputs)
    evidence["reason"] = reason
    return DimensionSnapshot(status=status, evidence=evidence)


def _resource_state_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    """Judge whether the runtime still has enough local resources to keep living."""

    runtime_exists = bool(inputs.get("runtime_path_exists"))
    runtime_writable = bool(inputs.get("runtime_writable"))
    disk_free_bytes = int(inputs.get("disk_free_bytes", 0))
    status = "healthy"
    reason = "resource_state_ok"
    if not runtime_exists:
        status = "critical"
        reason = "runtime_path_missing"
    elif not runtime_writable:
        status = "critical"
        reason = "runtime_not_writable"
    elif disk_free_bytes <= config.disk_critical_free_bytes:
        status = "critical"
        reason = "disk_space_critical"
    elif disk_free_bytes <= config.disk_degraded_free_bytes:
        status = "degraded"
        reason = "disk_space_declining"
    evidence = dict(inputs)
    evidence["reason"] = reason
    return DimensionSnapshot(status=status, evidence=evidence)


def _anomaly_accumulation_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    """Judge whether recent errors and abnormal events are accumulating too quickly."""

    error_count = int(inputs.get("recent_error_count", 0))
    yield_count = int(inputs.get("recent_yield_count", 0))
    distress_count = int(inputs.get("recent_distress_count", 0))
    restart_count = int(inputs.get("recent_restart_count", 0))
    anomaly_count = error_count + yield_count + distress_count + max(restart_count - 1, 0)
    status = "healthy"
    reason = "anomaly_window_quiet"
    if distress_count > 0 or anomaly_count >= config.anomaly_critical_count:
        status = "critical"
        reason = "anomaly_density_critical"
    elif anomaly_count >= config.anomaly_degraded_count:
        status = "degraded"
        reason = "anomaly_density_rising"
    evidence = dict(inputs)
    evidence["reason"] = reason
    return DimensionSnapshot(status=status, evidence=evidence)


def evaluate_dimensions(inputs: dict[str, dict[str, object]], config: ExternalLifeConfig) -> dict[str, DimensionSnapshot]:
    """Evaluate all supported external-life dimensions from raw patrol inputs."""

    return {
        "host_continuity": _host_continuity_snapshot(inputs["host_continuity"], config),
        "runtime_integrity": _runtime_integrity_snapshot(inputs["runtime_integrity"]),
        "resource_state": _resource_state_snapshot(inputs["resource_state"], config),
        "anomaly_accumulation": _anomaly_accumulation_snapshot(inputs["anomaly_accumulation"], config),
    }


def determine_overall_status(dimensions: dict[str, DimensionSnapshot]) -> str:
    """Collapse per-dimension judgments into the highest-severity overall status."""

    highest = max(SEVERITY_ORDER.get(snapshot.status, 0) for snapshot in dimensions.values())
    for status, rank in SEVERITY_ORDER.items():
        if rank == highest:
            return status
    return "healthy"


def determine_primary_gap(dimensions: dict[str, DimensionSnapshot]) -> dict[str, str]:
    """Pick the main survival gap using a fixed dimension priority order."""

    for dimension_name in DIMENSION_PRIORITY:
        snapshot = dimensions[dimension_name]
        if snapshot.status == "healthy":
            continue
        reason = str(snapshot.evidence.get("reason") or dimension_name)
        return {"type": dimension_name, "reason": reason}
    return {"type": "none", "reason": "none"}


def determine_trend(
    current_overall_status: str,
    previous_snapshot: ExternalLifeSnapshot | None,
) -> str:
    """Compare current overall severity with the previous snapshot to derive trend."""

    if previous_snapshot is None:
        return "unknown"
    current_rank = SEVERITY_ORDER.get(current_overall_status, 0)
    previous_rank = SEVERITY_ORDER.get(previous_snapshot.overall_status, 0)
    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    return "stable"
