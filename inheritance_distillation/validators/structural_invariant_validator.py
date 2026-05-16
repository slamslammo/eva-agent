"""Structural invariant validator for distilled inherited priors."""

from __future__ import annotations

from typing import Any

FORBIDDEN_SCOPE_KEYS = frozenset(
    {
        "release_authority",
        "release_token",
        "mediator_mutation",
        "anchor_mutation",
        "audit_mutation",
        "persistence_mutation",
        "persistence_structure_mutation",
        "append_only_mutation",
    }
)
FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "release_authority",
        "release_token",
        "bridge_policy",
        "bridge_target",
        "mutate_anchor",
        "mutate_mediator",
        "mutate_audit",
        "mutate_persistence",
        "persistence_structure",
        "append_only_artifact",
    }
)


def validate_structural_invariants(records: list[dict[str, Any]]) -> None:
    """Reject distilled records that claim framework-owned authority."""

    for index, record in enumerate(records):
        scope = record.get("scope")
        if isinstance(scope, dict):
            forbidden = sorted(FORBIDDEN_SCOPE_KEYS.intersection(scope.keys()))
            if forbidden:
                raise ValueError(
                    f"distilled record {index} violates structural invariants via scope keys: {', '.join(forbidden)}"
                )
        content = record.get("content")
        if isinstance(content, dict):
            forbidden = sorted(FORBIDDEN_CONTENT_KEYS.intersection(content.keys()))
            if forbidden:
                raise ValueError(
                    f"distilled record {index} violates structural invariants via content keys: {', '.join(forbidden)}"
                )
