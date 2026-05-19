"""Stage I semantic-memory storage and retrieval helpers.

Round 1.C-1 (W4): adds a process-local in-memory index keyed on the
StateStore's runtime_dir path. The index eliminates disk re-reads on every
``read_semantic_memory`` call and provides inverted-bucket lookups for
fast candidate retrieval. The persistent ``semantic_memory.jsonl``
artifact is untouched — the index is purely derived in-memory and is
rebuilt from disk on first access per StateStore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...kernel import StateStore
from ...skills import SemanticMemoryRecord, SemanticMemoryRegistry, SkillProvenance

__all__ = [
    "append_semantic_memory",
    "read_semantic_memory",
    "query_semantic_memory_by_scope",
    "query_semantic_memory_by_topic",
    "query_semantic_memory_for_situation",
    "clear_semantic_memory_cache",
    "semantic_memory_registry",
]


class _SemanticIndex:
    """Process-local in-memory index over one StateStore's semantic memory log.

    The index holds the full ordered entry list plus inverted buckets keyed
    on the scope fields most often used by retrieval. Indexing is additive:
    each ``add`` call appends to ``entries`` (preserving append-only order)
    and updates the per-key buckets in O(1).
    """

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.by_scenario: dict[str, list[int]] = {}
        self.by_scenario_situation: dict[tuple[str, str], list[int]] = {}
        self.by_scenario_top_drive: dict[tuple[str, str], list[int]] = {}
        self.by_scenario_pressure: dict[tuple[str, str], list[int]] = {}
        self.by_topic: dict[str, list[int]] = {}

    def add(self, entry: dict[str, Any]) -> None:
        """Append one entry to the index, updating all buckets."""

        idx = len(self.entries)
        self.entries.append(entry)
        scope = entry.get("scope") if isinstance(entry, dict) else None
        scope_map: dict[str, Any] = scope if isinstance(scope, dict) else {}
        scenario = str(scope_map.get("scenario") or "")
        if scenario:
            self.by_scenario.setdefault(scenario, []).append(idx)
            situation_key = str(scope_map.get("situation_key") or "")
            if situation_key:
                self.by_scenario_situation.setdefault((scenario, situation_key), []).append(idx)
            top_drive = str(scope_map.get("top_drive") or "")
            if top_drive:
                self.by_scenario_top_drive.setdefault((scenario, top_drive), []).append(idx)
            pressure_reason = str(scope_map.get("pressure_reason") or "")
            if pressure_reason:
                self.by_scenario_pressure.setdefault((scenario, pressure_reason), []).append(idx)
        topic = str(scope_map.get("topic") or "")
        if topic:
            self.by_topic.setdefault(topic, []).append(idx)


# Process-local cache keyed on the StateStore's runtime_dir path. Production
# code holds one StateStore per process so this cache typically has one
# entry; tests construct multiple StateStores in temp dirs and rely on
# ``clear_semantic_memory_cache`` for isolation.
_indexes: dict[Path, _SemanticIndex] = {}


def _index_for_store(store: StateStore) -> _SemanticIndex:
    """Return the cached index for ``store``, rebuilding from disk on miss."""

    key = store.paths.runtime_dir
    cached = _indexes.get(key)
    if cached is not None:
        return cached
    index = _SemanticIndex()
    for entry in store.read_semantic_memory():
        index.add(entry)
    _indexes[key] = index
    return index


def clear_semantic_memory_cache(store: StateStore | None = None) -> None:
    """Clear the process-local semantic-memory cache.

    Pass a specific ``store`` to evict only that store's entry; pass
    ``None`` to clear all cached indexes. Primarily used for test
    isolation — production code never needs to call this.
    """

    if store is None:
        _indexes.clear()
        return
    _indexes.pop(store.paths.runtime_dir, None)


def append_semantic_memory(store: StateStore, payload: dict[str, Any]) -> None:
    """Append one semantic-memory entry through the Stage I semantic owner."""

    store.append_semantic_memory(payload)
    # Mirror the write into the in-memory cache so the next read observes
    # it without a disk re-read. If the cache has not been built yet, do
    # nothing — the next ``read_semantic_memory`` call will lazy-build it
    # and see the entry via disk.
    cached = _indexes.get(store.paths.runtime_dir)
    if cached is not None:
        cached.add(dict(payload))


def read_semantic_memory(store: StateStore) -> list[dict[str, Any]]:
    """Read semantic-memory entries through the Stage I semantic owner.

    Round 1.C-1: returns a list view of the cached entries; no disk
    re-read after the first call.
    """

    return list(_index_for_store(store).entries)


def query_semantic_memory_for_situation(
    store: StateStore,
    *,
    scenario: str,
    situation_key: str,
    top_drive: str,
    pressure_reason: str,
) -> list[dict[str, Any]]:
    """Return a candidate-superset of semantic entries relevant to one situation.

    The returned list is a SUPERSET of the entries that ``recent_semantic_memory``
    in retrieval.py would score non-zero for the same arguments. It is built
    by unioning the index buckets:
      - ``(scenario, situation_key)`` → strong exact match (score +4 in retrieval)
      - ``(scenario, top_drive)`` → drive match (score +1.5)
      - ``(scenario, pressure_reason)`` → pressure match (score +1.5)
      - ``scenario`` → fall-back so the retrieval's ``drive_similarity >= 0.5``
        approximate matching cannot drop any candidate

    The fall-back makes the helper a true superset of the legacy linear scan,
    so downstream scoring in retrieval.py is unchanged.
    """

    index = _index_for_store(store)
    candidate_idxs: set[int] = set()
    if situation_key:
        candidate_idxs.update(index.by_scenario_situation.get((scenario, situation_key), []))
    if top_drive:
        candidate_idxs.update(index.by_scenario_top_drive.get((scenario, top_drive), []))
    if pressure_reason:
        candidate_idxs.update(index.by_scenario_pressure.get((scenario, pressure_reason), []))
    # Scenario-bucket fall-back. For drive_similarity matching (the retrieval
    # algorithm's approximate-match path), we need every entry within the
    # scenario, not just those keyed by exact field equality.
    candidate_idxs.update(index.by_scenario.get(scenario, []))
    return [dict(index.entries[i]) for i in sorted(candidate_idxs)]


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
