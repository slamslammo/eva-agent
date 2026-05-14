"""Linux runtime dimension judgment policy for H-0F."""

from __future__ import annotations

from typing import Any

from eva.kernel import DimensionSnapshot, ExternalLifeConfig
from eva.persistence_targets import get_default_persistence_hierarchy


def _rate_context(inputs: dict[str, object]) -> dict[str, Any]:
    value = inputs.get("rate_context")
    return dict(value) if isinstance(value, dict) else {}


def _rate_available(inputs: dict[str, object]) -> bool:
    return bool(_rate_context(inputs).get("available"))


def _rate_direction_from_inputs(inputs: dict[str, object]) -> str:
    direction = _rate_context(inputs).get("direction")
    return str(direction) if isinstance(direction, str) else "unknown"


def _float_value(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _runtime_integrity_persistence_projection(*, instance_valid: bool, required_present: bool, runtime_writable: bool) -> dict[str, Any]:
    hierarchy = get_default_persistence_hierarchy()
    context = {
        "instance_valid": instance_valid,
        "runtime_files_missing": not required_present,
        "runtime_not_writable": not runtime_writable,
        "runtime_path_missing": False,
    }
    failed = hierarchy.failed_targets(context)
    return {
        "failed_levels": [target.level for target in failed],
        "level_1_local_unrecoverable_forbidden": hierarchy.local_unrecoverable_failure_forbidden(1),
    }


def host_continuity_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
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


def runtime_integrity_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    del config
    required_present = all(bool(inputs.get(key)) for key in ("active_instance_present", "runtime_state_present", "events_present", "lock_present"))
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
    evidence["persistence_hierarchy"] = _runtime_integrity_persistence_projection(
        instance_valid=instance_valid,
        required_present=required_present,
        runtime_writable=runtime_writable,
    )
    return DimensionSnapshot(status=status, evidence=evidence)


def resource_state_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
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


def anomaly_accumulation_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
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


__all__ = [
    "anomaly_accumulation_snapshot",
    "host_continuity_snapshot",
    "resource_state_snapshot",
    "runtime_integrity_snapshot",
]
