"""Crafter dimension judgment specs for Stage H H-0F."""

from __future__ import annotations

from eva.kernel import DimensionSnapshot, ExternalLifeConfig


def _snapshot_from_payload(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    del config
    status = str(inputs.get("status") or "healthy")
    return DimensionSnapshot(status=status, evidence=dict(inputs))


def avatar_safety_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def avatar_metabolic_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def avatar_recovery_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def inventory_capability_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def inventory_acquisition_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def local_view_threat_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def local_view_resource_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


def local_view_utility_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
    return _snapshot_from_payload(inputs, config)


__all__ = [
    "avatar_metabolic_snapshot",
    "avatar_recovery_snapshot",
    "avatar_safety_snapshot",
    "inventory_acquisition_snapshot",
    "inventory_capability_snapshot",
    "local_view_resource_snapshot",
    "local_view_threat_snapshot",
    "local_view_utility_snapshot",
]
