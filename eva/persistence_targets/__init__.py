"""Persistence target hierarchy for explicit survival semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


PersistenceFailureCondition = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class PersistenceTarget:
    """One explicit persistence target in the current runtime hierarchy."""

    level: int
    name: str
    failure_condition: PersistenceFailureCondition
    active: bool = True
    dependencies: tuple[int, ...] = ()
    transfer_channel: str | None = None

    def has_failed(self, context: dict[str, Any]) -> bool:
        """Return whether this target has failed under the provided context."""

        return bool(self.failure_condition(dict(context)))


@dataclass(frozen=True)
class PersistenceHierarchy:
    """Explicit collection of persistence targets activated for one runtime."""

    targets: tuple[PersistenceTarget, ...] = field(default_factory=tuple)

    def active_targets(self) -> tuple[PersistenceTarget, ...]:
        return tuple(target for target in self.targets if target.active)

    def failed_targets(self, context: dict[str, Any]) -> tuple[PersistenceTarget, ...]:
        return tuple(target for target in self.active_targets() if target.has_failed(context))

    def targets_at_risk(self, context: dict[str, Any]) -> tuple[PersistenceTarget, ...]:
        failed_levels = {target.level for target in self.failed_targets(context)}
        if not failed_levels:
            return ()
        return tuple(
            target
            for target in self.active_targets()
            if any(level in failed_levels for level in target.dependencies)
        )

    def target_for_level(self, level: int) -> PersistenceTarget | None:
        for target in self.targets:
            if target.level == level:
                return target
        return None

    def dependency_failures(self, context: dict[str, Any]) -> dict[int, tuple[int, ...]]:
        failed_levels = {target.level for target in self.failed_targets(context)}
        result: dict[int, tuple[int, ...]] = {}
        for target in self.active_targets():
            broken = tuple(level for level in target.dependencies if level in failed_levels)
            if broken:
                result[target.level] = broken
        return result

    def local_unrecoverable_failure_forbidden(self, level: int) -> bool:
        target = self.target_for_level(level)
        if target is None or not target.active:
            return False
        return target.transfer_channel is None

    def can_locally_authorize_unrecoverable_failure(self, level: int) -> bool:
        return not self.local_unrecoverable_failure_forbidden(level)


_DEFAULT_PERSISTENCE_HIERARCHY: PersistenceHierarchy | None = None


def register_default_persistence_hierarchy(hierarchy: PersistenceHierarchy) -> None:
    """Register the active persistence hierarchy for the current runtime context."""

    global _DEFAULT_PERSISTENCE_HIERARCHY
    _DEFAULT_PERSISTENCE_HIERARCHY = hierarchy


def get_default_persistence_hierarchy() -> PersistenceHierarchy:
    """Return the active persistence hierarchy for the current runtime context."""

    global _DEFAULT_PERSISTENCE_HIERARCHY
    if _DEFAULT_PERSISTENCE_HIERARCHY is None:
        raise RuntimeError(
            "no persistence hierarchy registered; activate a scenario and register its persistence hierarchy before use"
        )
    return _DEFAULT_PERSISTENCE_HIERARCHY


def build_linux_runtime_persistence_hierarchy() -> PersistenceHierarchy:
    """Return the minimal Linux runtime persistence hierarchy for Stage G."""

    def level_1_failure(context: dict[str, Any]) -> bool:
        return not bool(context.get("instance_valid", False))

    def level_4_failure(context: dict[str, Any]) -> bool:
        return bool(
            context.get("runtime_path_missing", False)
            or context.get("runtime_files_missing", False)
            or context.get("runtime_not_writable", False)
        )

    return PersistenceHierarchy(
        targets=(
            PersistenceTarget(
                level=1,
                name="substrate_instance",
                failure_condition=level_1_failure,
                active=True,
                dependencies=(),
                transfer_channel=None,
            ),
            PersistenceTarget(
                level=4,
                name="runtime_artifact_substrate",
                failure_condition=level_4_failure,
                active=True,
                dependencies=(1,),
                transfer_channel=None,
            ),
        )
    )


__all__ = [
    "PersistenceHierarchy",
    "PersistenceTarget",
    "build_linux_runtime_persistence_hierarchy",
    "get_default_persistence_hierarchy",
    "register_default_persistence_hierarchy",
]
