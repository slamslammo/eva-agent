"""Stage I semantic-memory storage and retrieval helpers."""

from __future__ import annotations

from typing import Any

from ...kernel import StateStore
from ...skills import SemanticMemoryRecord, SemanticMemoryRegistry, SkillProvenance

__all__ = [
    "append_semantic_memory",
    "read_semantic_memory",
    "query_semantic_memory_by_scope",
    "query_semantic_memory_by_topic",
    "semantic_memory_registry",
]


def append_semantic_memory(store: StateStore, payload: dict[str, Any]) -> None:
    """Append one semantic-memory entry through the Stage I semantic owner."""

    store.append_semantic_memory(payload)


def read_semantic_memory(store: StateStore) -> list[dict[str, Any]]:
    """Read semantic-memory entries through the Stage I semantic owner."""

    return store.read_semantic_memory()


def query_semantic_memory_by_topic(
    semantic_entries: list[dict[str, Any]],
    *,
    topic: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return semantic-memory entries whose scope topic matches exactly."""

    matches = [
        dict(entry)
        for entry in semantic_entries
        if str((entry.get("scope") or {}).get("topic") or "") == topic
    ]
    matches.sort(key=lambda entry: (float(entry.get("confidence", 0.0)), str(entry.get("recorded_at") or "")), reverse=True)
    if limit is None:
        return matches
    return matches[:limit]


def query_semantic_memory_by_scope(
    semantic_entries: list[dict[str, Any]],
    *,
    limit: int | None = None,
    **scope_filters: Any,
) -> list[dict[str, Any]]:
    """Return semantic-memory entries whose scope matches the provided exact filters."""

    matches = [
        dict(entry)
        for entry in semantic_entries
        if _scope_matches(entry.get("scope"), scope_filters)
    ]
    matches.sort(key=lambda entry: (float(entry.get("confidence", 0.0)), str(entry.get("recorded_at") or "")), reverse=True)
    if limit is None:
        return matches
    return matches[:limit]


def semantic_memory_registry(
    semantic_entries: list[dict[str, Any]] | None = None,
) -> SemanticMemoryRegistry:
    """Return one semantic-memory registry over persisted Stage I semantic entries."""

    records = [
        SemanticMemoryRecord(
            recorded_at=str(entry.get("recorded_at") or ""),
            pattern_summary=str(entry.get("pattern_summary") or ""),
            extracted_from_episodes=tuple(str(ref) for ref in entry.get("extracted_from_episodes", [])),
            confidence=float(entry.get("confidence", 0.0)),
            scope=dict(entry.get("scope") or {}),
            provenance=_provenance_from_entry(entry),
            preferred_candidate_profiles=tuple(
                str(profile)
                for profile in entry.get("preferred_candidate_profiles", [])
                if profile is not None
            ),
        )
        for entry in (semantic_entries or [])
    ]
    return SemanticMemoryRegistry(records)


def _scope_matches(scope_payload: Any, scope_filters: dict[str, Any]) -> bool:
    if not isinstance(scope_payload, dict):
        return False
    return all(scope_payload.get(key) == value for key, value in scope_filters.items())


def _provenance_from_entry(entry: dict[str, Any]) -> SkillProvenance:
    payload = entry.get("provenance") or {}
    return SkillProvenance(
        source=str(payload.get("source") or "experience"),
        provenance_detail=str(payload.get("provenance_detail") or "stage_i_semantic_memory"),
        confidence=float(payload.get("confidence", entry.get("confidence", 0.0))),
        scope=dict(payload.get("scope") or {}),
        mutable=bool(payload.get("mutable", True)),
    )
