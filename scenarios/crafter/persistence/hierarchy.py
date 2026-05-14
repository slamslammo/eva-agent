"""Crafter persistence hierarchy for Stage H H-3."""

from __future__ import annotations

from eva.persistence_targets import PersistenceHierarchy, PersistenceTarget


def build_crafter_persistence_hierarchy() -> PersistenceHierarchy:
    def level_1_failure(context: dict[str, object]) -> bool:
        return not bool(context.get("instance_valid", False))

    def level_2_failure(context: dict[str, object]) -> bool:
        health = context.get("avatar_health")
        try:
            return float(health) <= 0.0
        except (TypeError, ValueError):
            return bool(context.get("avatar_dead", False))

    def level_3_failure(context: dict[str, object]) -> bool:
        return bool(context.get("critical_capability_missing", False))

    def level_4_failure(context: dict[str, object]) -> bool:
        return bool(context.get("critical_resource_missing", False))

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
                level=2,
                name="crafter_avatar_instance",
                failure_condition=level_2_failure,
                active=True,
                dependencies=(1,),
                transfer_channel=None,
            ),
            PersistenceTarget(
                level=3,
                name="crafter_capability_structure",
                failure_condition=level_3_failure,
                active=True,
                dependencies=(1, 2),
                transfer_channel=None,
            ),
            PersistenceTarget(
                level=4,
                name="crafter_resource_system",
                failure_condition=level_4_failure,
                active=True,
                dependencies=(1, 2),
                transfer_channel=None,
            ),
        )
    )


__all__ = ["build_crafter_persistence_hierarchy"]
