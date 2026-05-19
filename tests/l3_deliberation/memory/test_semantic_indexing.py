"""Round 1.C-1 (W4): pin the process-local index over semantic memory.

The semantic-memory index lives in ``eva/l3_deliberation/memory/semantic.py``
as a module-level cache keyed on ``StateStore.paths.runtime_dir``. It does
three jobs:

1. Eliminate disk re-reads on every ``read_semantic_memory`` call. Once an
   index is built from the disk-backed log, subsequent reads return the
   cached entries list directly.
2. Make ``append_semantic_memory`` synchronously update the cache so the
   next read observes the new entry.
3. Provide inverted lookups by ``(scenario, situation_key)``,
   ``(scenario, top_drive)``, ``(scenario, pressure_reason)``, ``topic``, and
   ``scenario`` for future retrieval optimizations. The
   ``query_semantic_memory_for_situation`` helper combines these buckets
   with a scenario-bucket fallback so callers can request a pre-filtered
   candidate list without losing matches that would have been picked up by
   the legacy linear scan.

Tests exercise the public API only. The internal index class is an
implementation detail.
"""

from __future__ import annotations

import tempfile
import unittest

from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation.memory import (
    append_semantic_memory,
    read_semantic_memory,
)
from eva.l3_deliberation.memory.semantic import (
    clear_semantic_memory_cache,
    query_semantic_memory_for_situation,
)


def _entry(
    *,
    recorded_at: str,
    scenario: str,
    topic: str,
    situation_key: str,
    top_drive: str,
    life_state: str = "STABLE",
    pressure_reason: str = "none",
    preferred_candidate_profiles: tuple[str, ...] = ("observe_first",),
    confidence: float = 0.7,
    pattern_summary: str = "test-pattern",
) -> dict[str, object]:
    return {
        "recorded_at": recorded_at,
        "pattern_summary": pattern_summary,
        "extracted_from_episodes": [],
        "confidence": confidence,
        "scope": {
            "scenario": scenario,
            "topic": topic,
            "situation_key": situation_key,
            "top_drive": top_drive,
            "life_state": life_state,
            "pressure_reason": pressure_reason,
        },
        "preferred_candidate_profiles": list(preferred_candidate_profiles),
        "provenance": {
            "source": "experience",
            "provenance_detail": "stage_i_semantic_memory",
            "confidence": confidence,
            "scope": {"scenario": scenario},
            "mutable": True,
        },
    }


class SemanticMemoryCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_semantic_memory_cache()

    def tearDown(self) -> None:
        clear_semantic_memory_cache()

    def test_cold_read_on_empty_store_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            self.assertEqual(read_semantic_memory(store), [])

    def test_append_visible_to_next_read_without_disk_re_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            entry = _entry(
                recorded_at="2026-05-01T00:00:00Z",
                scenario="crafter",
                topic="explore_first_pattern",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
            )
            append_semantic_memory(store, entry)
            entries = read_semantic_memory(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["recorded_at"], "2026-05-01T00:00:00Z")

    def test_two_appends_visible_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            for ts in ("2026-05-01T00:00:00Z", "2026-05-02T00:00:00Z"):
                append_semantic_memory(
                    store,
                    _entry(
                        recorded_at=ts,
                        scenario="crafter",
                        topic="t",
                        situation_key="metabolic|STABLE|food_low",
                        top_drive="metabolic",
                    ),
                )
            entries = read_semantic_memory(store)
            self.assertEqual([e["recorded_at"] for e in entries], [
                "2026-05-01T00:00:00Z",
                "2026-05-02T00:00:00Z",
            ])

    def test_cache_isolation_across_stores(self) -> None:
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            store1 = StateStore(build_runtime_paths(t1))
            store2 = StateStore(build_runtime_paths(t2))
            append_semantic_memory(
                store1,
                _entry(
                    recorded_at="2026-05-01T00:00:00Z",
                    scenario="crafter",
                    topic="t",
                    situation_key="exploration|STABLE|none",
                    top_drive="exploration",
                ),
            )
            self.assertEqual(len(read_semantic_memory(store1)), 1)
            self.assertEqual(read_semantic_memory(store2), [])

    def test_clear_semantic_memory_cache_forces_rebuild_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            append_semantic_memory(
                store,
                _entry(
                    recorded_at="2026-05-01T00:00:00Z",
                    scenario="crafter",
                    topic="t",
                    situation_key="exploration|STABLE|none",
                    top_drive="exploration",
                ),
            )
            self.assertEqual(len(read_semantic_memory(store)), 1)
            clear_semantic_memory_cache(store)
            # Next read should rebuild from disk; entries persist on disk.
            self.assertEqual(len(read_semantic_memory(store)), 1)

    def test_clear_semantic_memory_cache_without_store_clears_all(self) -> None:
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            store1 = StateStore(build_runtime_paths(t1))
            store2 = StateStore(build_runtime_paths(t2))
            append_semantic_memory(
                store1,
                _entry(
                    recorded_at="2026-05-01T00:00:00Z",
                    scenario="crafter",
                    topic="t",
                    situation_key="a|STABLE|none",
                    top_drive="a",
                ),
            )
            append_semantic_memory(
                store2,
                _entry(
                    recorded_at="2026-05-01T00:00:00Z",
                    scenario="crafter",
                    topic="t",
                    situation_key="b|STABLE|none",
                    top_drive="b",
                ),
            )
            self.assertEqual(len(read_semantic_memory(store1)), 1)
            self.assertEqual(len(read_semantic_memory(store2)), 1)
            clear_semantic_memory_cache()  # clears all
            # Caches rebuilt on next read, entries still on disk.
            self.assertEqual(len(read_semantic_memory(store1)), 1)
            self.assertEqual(len(read_semantic_memory(store2)), 1)


class SemanticMemoryIndexedQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_semantic_memory_cache()

    def tearDown(self) -> None:
        clear_semantic_memory_cache()

    def _seed_diverse_entries(self, store: StateStore) -> None:
        """Seed entries spanning multiple scenarios / drives / situations."""

        rows = [
            _entry(
                recorded_at="2026-05-01T00:00:00Z",
                scenario="crafter",
                topic="explore",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
                preferred_candidate_profiles=("observe_first",),
            ),
            _entry(
                recorded_at="2026-05-02T00:00:00Z",
                scenario="crafter",
                topic="safety_response",
                situation_key="safety|STABLE|threat_visible",
                top_drive="safety",
                pressure_reason="threat_visible",
                preferred_candidate_profiles=("escalate_first",),
            ),
            _entry(
                recorded_at="2026-05-03T00:00:00Z",
                scenario="crafter",
                topic="metabolic",
                situation_key="metabolic|STABLE|food_low",
                top_drive="metabolic",
                pressure_reason="food_low",
                preferred_candidate_profiles=("stabilize_first",),
            ),
            _entry(
                recorded_at="2026-05-04T00:00:00Z",
                scenario="linux_runtime",
                topic="integrity",
                situation_key="integrity|STABLE|none",
                top_drive="integrity",
                preferred_candidate_profiles=("stabilize_first",),
            ),
        ]
        for row in rows:
            append_semantic_memory(store, row)

    def test_query_filters_by_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            self._seed_diverse_entries(store)
            crafter_only = query_semantic_memory_for_situation(
                store,
                scenario="crafter",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
                pressure_reason="none",
            )
            scenarios = {str(e["scope"]["scenario"]) for e in crafter_only}
            self.assertEqual(scenarios, {"crafter"})

    def test_query_returns_situation_key_match_plus_scenario_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            self._seed_diverse_entries(store)
            results = query_semantic_memory_for_situation(
                store,
                scenario="crafter",
                situation_key="safety|STABLE|threat_visible",
                top_drive="safety",
                pressure_reason="threat_visible",
            )
            keys = {str(e["scope"]["situation_key"]) for e in results}
            # Must include the exact situation_key match.
            self.assertIn("safety|STABLE|threat_visible", keys)
            # Must include the scenario-bucket fallback (other crafter entries).
            self.assertIn("exploration|STABLE|none", keys)
            self.assertIn("metabolic|STABLE|food_low", keys)

    def test_query_returns_superset_of_recent_semantic_memory_candidates(self) -> None:
        """The indexed query must return a SUPERSET of what the legacy linear
        scan in ``recent_semantic_memory`` would consider non-zero. This is
        the equivalence safety net: scoring is unchanged downstream, only
        the input set is narrowed."""

        from eva.l3_deliberation.memory.retrieval import recent_semantic_memory

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            self._seed_diverse_entries(store)

            indexed = query_semantic_memory_for_situation(
                store,
                scenario="crafter",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
                pressure_reason="none",
            )
            scored_from_indexed = recent_semantic_memory(
                indexed,
                scenario="crafter",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
                life_state="STABLE",
                pressure_reason="none",
                limit=10,
            )

            full_entries = read_semantic_memory(store)
            scored_from_full = recent_semantic_memory(
                full_entries,
                scenario="crafter",
                situation_key="exploration|STABLE|none",
                top_drive="exploration",
                life_state="STABLE",
                pressure_reason="none",
                limit=10,
            )

            # The scored outputs must match exactly — narrowing the input must
            # not drop any candidate that scored non-zero against full input.
            self.assertEqual(
                [r["recorded_at"] for r in scored_from_indexed],
                [r["recorded_at"] for r in scored_from_full],
            )


if __name__ == "__main__":
    unittest.main()
