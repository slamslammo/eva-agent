"""Framework drive preset seams and generic update policy surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..scenario_bundle import get_active_runtime_scenario


@dataclass(frozen=True)
class DriveUpdatePolicy:
    """Explicit parameter surface for one L2 drive reconciliation step."""

    base_decay: float = 0.05
    severity_degraded_delta: float = 0.18
    severity_critical_delta: float = 0.36
    threat_bonus: float = 0.04
    curiosity_recovery: float = 0.08
    curiosity_suppression: float = 0.12
    # Phase-1.5 tuning: whether ``_curiosity_delta`` suppression fires when
    # ``overall_status`` is degraded/critical (in addition to firing on
    # threat). Linux semantics keep this True so curiosity is dampened
    # whenever the runtime is in any degraded state. Crafter sets this to
    # False because the avatar is in degraded state almost continuously
    # (food/water/energy slowly tick down), making suppression dominate over
    # recovery and pinning exploration drive level at 0 indefinitely.
    curiosity_suppress_on_degraded_status: bool = True
    # Fix-C: drive update mode. "accumulate" (default) is the original
    # linear -decay + Σseverity_delta integration — kept for Linux and all
    # existing behavior. "approach" instead moves each risk drive toward a
    # severity-derived *target* (critical→target_critical, degraded→
    # target_degraded, healthy→0) at ``approach_rate``, so sustained pressure
    # settles at a sub-1.0 layered steady state instead of pinning every drive
    # at 1.0 (which collapses drive-impact scoring). Scenarios opt in per preset.
    update_mode: str = "accumulate"
    approach_rate: float = 0.3
    target_critical: float = 0.9
    target_degraded: float = 0.55


@dataclass(frozen=True)
class DrivePreset:
    """Scenario-supplied drive family, mapping, and default policy bundle."""

    drive_types: tuple[str, ...]
    drive_type_by_dimension: dict[str, str]
    default_policy: DriveUpdatePolicy = field(default_factory=DriveUpdatePolicy)
    curiosity_drive_type: str | None = None

    def drive_for_dimension(self, dimension_name: str) -> str | None:
        """Return the configured drive type for one sensed dimension."""

        return self.drive_type_by_dimension.get(dimension_name)

    def is_curiosity_drive(self, drive_type: str) -> bool:
        """Return whether the given drive type uses curiosity recovery semantics."""

        return self.curiosity_drive_type is not None and drive_type == self.curiosity_drive_type


class DriveRegistry(Protocol):
    """Minimal registry surface that can provide the active drive preset."""

    def default_preset(self) -> DrivePreset:
        """Return the currently active drive preset."""


_DEFAULT_DRIVE_PRESET: DrivePreset | None = None


def register_default_drive_preset(preset: DrivePreset) -> None:
    """Register the active drive preset for the current runtime context."""

    global _DEFAULT_DRIVE_PRESET
    _DEFAULT_DRIVE_PRESET = preset


def get_default_drive_preset() -> DrivePreset:
    """Return the active drive preset, defaulting to the active scenario during Phase A."""

    global _DEFAULT_DRIVE_PRESET
    if _DEFAULT_DRIVE_PRESET is None:
        _DEFAULT_DRIVE_PRESET = get_active_runtime_scenario().drive_preset
    return _DEFAULT_DRIVE_PRESET


def severity_delta_for_status(status: str, policy: DriveUpdatePolicy) -> float:
    """Return the configured severity accumulation for one judged status."""

    if status == "critical":
        return policy.severity_critical_delta
    if status == "degraded":
        return policy.severity_degraded_delta
    return 0.0


def severity_target_for_status(status: str, policy: DriveUpdatePolicy) -> float:
    """Return the approach-mode target level for one judged status (Fix-C)."""

    if status == "critical":
        return policy.target_critical
    if status == "degraded":
        return policy.target_degraded
    return 0.0


__all__ = [
    "DrivePreset",
    "DriveRegistry",
    "DriveUpdatePolicy",
    "get_default_drive_preset",
    "register_default_drive_preset",
    "severity_delta_for_status",
    "severity_target_for_status",
]
