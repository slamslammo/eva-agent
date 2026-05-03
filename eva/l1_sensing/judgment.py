"""Turn sensed external-life inputs into deterministic health judgments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..kernel import DimensionSnapshot, ExternalLifeConfig, ExternalLifeSnapshot

SEVERITY_ORDER = {"healthy": 0, "degraded": 1, "critical": 2}
DIMENSION_PRIORITY = [
    "runtime_integrity",
    "host_continuity",
    "resource_state",
    "anomaly_accumulation",
]


def _rank_for_status(value: str) -> int:
    """Return the numeric severity rank for one status label."""

    return SEVERITY_ORDER.get(value, 0)


def _rate_context(inputs: dict[str, object]) -> dict[str, Any]:
    """Return the normalized rate-context payload for one dimension."""

    value = inputs.get("rate_context")
    if isinstance(value, dict):
        return dict(value)
    return {}


def _rate_available(inputs: dict[str, object]) -> bool:
    """Return whether rate evidence is available for one dimension."""

    return bool(_rate_context(inputs).get("available"))


def _rate_direction_from_inputs(inputs: dict[str, object]) -> str:
    """Return the coarse direction label derived by sensing."""

    direction = _rate_context(inputs).get("direction")
    if isinstance(direction, str):
        return direction
    return "unknown"


def _rate_direction(snapshot: DimensionSnapshot | None) -> str:
    """Extract the coarse direction from one dimension snapshot."""

    if snapshot is None:
        return "unknown"
    rate_context = snapshot.evidence.get("rate_context")
    if not isinstance(rate_context, dict):
        return "unknown"
    direction = rate_context.get("direction")
    if isinstance(direction, str):
        return direction
    return "unknown"


def _float_value(payload: dict[str, Any], key: str) -> float | None:
    """Read one numeric payload value when present."""

    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    elif _rate_available(inputs) and _rate_direction_from_inputs(inputs) == "worsening":
        near_degraded = restart_count >= max(config.continuity_restart_degraded_count - 1, 1)
        if near_degraded:
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
    consecutive_failures = int(inputs.get("consecutive_failures", 0))
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
    elif _rate_available(inputs) and _rate_direction_from_inputs(inputs) == "worsening" and consecutive_failures > 0:
        status = "degraded"
        reason = "heartbeat_miss_trend"
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
    elif _rate_available(inputs) and _rate_direction_from_inputs(inputs) == "worsening":
        rate_context = _rate_context(inputs)
        disk_delta = _float_value(rate_context, "disk_free_bytes_delta")
        if disk_delta is not None and disk_delta < 0:
            headroom_to_degraded = disk_free_bytes - config.disk_degraded_free_bytes
            if headroom_to_degraded <= abs(disk_delta):
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
    anomaly_count = int(inputs.get("anomaly_count", error_count + yield_count + distress_count + max(restart_count - 1, 0)))
    status = "healthy"
    reason = "anomaly_window_quiet"
    if distress_count > 0 or anomaly_count >= config.anomaly_critical_count:
        status = "critical"
        reason = "anomaly_density_critical"
    elif anomaly_count >= config.anomaly_degraded_count:
        status = "degraded"
        reason = "anomaly_density_rising"
    elif _rate_available(inputs) and _rate_direction_from_inputs(inputs) == "worsening":
        near_degraded = anomaly_count >= max(config.anomaly_degraded_count - 1, 1)
        if near_degraded:
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


def build_external_life_snapshot(
    cadence: str,
    inputs: dict[str, dict[str, object]],
    config: ExternalLifeConfig,
    now: datetime,
    *,
    previous_snapshot: ExternalLifeSnapshot | None = None,
) -> ExternalLifeSnapshot:
    """Build one judged patrol snapshot from raw sensing inputs."""

    dimensions = evaluate_dimensions(inputs, config)
    overall_status = determine_overall_status(dimensions)
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol=cadence,
        dimensions=dimensions,
        overall_status=overall_status,
        primary_gap=determine_primary_gap(dimensions),
        trend=determine_trend(
            overall_status,
            previous_snapshot,
            current_dimensions=dimensions,
        ),
        updated_at=now,
    )


def _dimension_trend(
    current_dimensions: dict[str, DimensionSnapshot],
    previous_snapshot: ExternalLifeSnapshot,
) -> str:
    """Compare current and previous dimensions when overall severity is unchanged."""

    for dimension_name in DIMENSION_PRIORITY:
        current = current_dimensions.get(dimension_name)
        previous = previous_snapshot.dimensions.get(dimension_name)
        current_rank = _rank_for_status("healthy" if current is None else current.status)
        previous_rank = _rank_for_status("healthy" if previous is None else previous.status)
        if current_rank > previous_rank:
            return "worsening"
        if current_rank < previous_rank:
            return "improving"
        direction = _rate_direction(current)
        if direction in {"worsening", "improving"}:
            return direction
    return "stable"


def determine_overall_status(dimensions: dict[str, DimensionSnapshot]) -> str:
    """Collapse per-dimension judgments into the highest-severity overall status."""

    highest = max(_rank_for_status(snapshot.status) for snapshot in dimensions.values())
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
    *,
    current_dimensions: dict[str, DimensionSnapshot] | None = None,
) -> str:
    """Compare current status with the previous snapshot to derive trend."""

    if previous_snapshot is None:
        return "unknown"
    current_rank = _rank_for_status(current_overall_status)
    previous_rank = _rank_for_status(previous_snapshot.overall_status)
    if current_rank > previous_rank:
        return "worsening"
    if current_rank < previous_rank:
        return "improving"
    if current_dimensions is None:
        return "stable"
    return _dimension_trend(current_dimensions, previous_snapshot)
