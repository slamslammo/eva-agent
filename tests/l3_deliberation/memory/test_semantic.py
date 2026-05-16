from __future__ import annotations

import tempfile
import unittest

from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation.memory import (
    append_semantic_memory,
    query_semantic_memory_by_scope,
    query_semantic_memory_by_topic,
    read_semantic_memory,
    semantic_memory_registry,
)


class SemanticMemoryTests(unittest.TestCase):
    def test_query_semantic_memory_by_topic_and_scope(self) -> None:
        entries = [
            {
                "recorded_at": "2026-05-01T00:00:00Z",
                "pattern_summary": "stabilize-first pattern",
                "extracted_from_episodes": ["2026-04-30T00:00:00Z"],
                "confidence": 0.8,
                "scope": {
                    "scenario": "linux_runtime",
                    "topic": "compatibility_release",
                    "situation_key": "integrity|STABLE|none",
                    "top_drive": "integrity",
                    "life_state": "STABLE",
                    "pressure_reason": "none",
                },
                "preferred_candidate_profiles": ["stabilize_first"],
                "provenance": {
                    "source": "experience",
                    "provenance_detail": "stage_i_semantic_memory",
                    "confidence": 0.8,
                    "scope": {"scenario": "linux_runtime"},
                    "mutable": True,
                },
            },
            {
                "recorded_at": "2026-05-02T00:00:00Z",
                "pattern_summary": "observe-first pattern",
                "extracted_from_episodes": ["2026-05-01T00:00:00Z"],
                "confidence": 0.6,
                "scope": {
                    "scenario": "crafter",
                    "topic": "compatibility_release",
                    "situation_key": "curiosity|STABLE|none",
                    "top_drive": "curiosity",
                    "life_state": "STABLE",
                    "pressure_reason": "none",
                },
                "preferred_candidate_profiles": ["observe_first"],
                "provenance": {
                    "source": "experience",
                    "provenance_detail": "stage_i_semantic_memory",
                    "confidence": 0.6,
                    "scope": {"scenario": "crafter"},
                    "mutable": True,
                },
            },
        ]

        by_topic = query_semantic_memory_by_topic(entries, topic="compatibility_release")
        self.assertEqual(len(by_topic), 2)
        self.assertGreaterEqual(by_topic[0]["confidence"], by_topic[1]["confidence"])

        by_scope = query_semantic_memory_by_scope(
            entries,
            scenario="linux_runtime",
            situation_key="integrity|STABLE|none",
        )
        self.assertEqual(len(by_scope), 1)
        self.assertEqual(by_scope[0]["preferred_candidate_profiles"], ["stabilize_first"])

    def test_semantic_memory_registry_wraps_records_with_provenance(self) -> None:
        registry = semantic_memory_registry(
            [
                {
                    "recorded_at": "2026-05-01T00:00:00Z",
                    "pattern_summary": "stabilize-first pattern",
                    "extracted_from_episodes": ["2026-04-30T00:00:00Z"],
                    "confidence": 0.8,
                    "scope": {"scenario": "linux_runtime", "topic": "compatibility_release"},
                    "preferred_candidate_profiles": ["stabilize_first"],
                    "provenance": {
                        "source": "experience",
                        "provenance_detail": "stage_i_semantic_memory",
                        "confidence": 0.8,
                        "scope": {"scenario": "linux_runtime"},
                        "mutable": True,
                    },
                }
            ]
        )

        records = registry.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].pattern_summary, "stabilize-first pattern")
        self.assertEqual(records[0].preferred_candidate_profiles, ("stabilize_first",))
        self.assertEqual(records[0].provenance.scope["scenario"], "linux_runtime")

    def test_append_and_read_semantic_memory_round_trips_through_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            append_semantic_memory(
                store,
                {
                    "recorded_at": "2026-05-01T00:00:00Z",
                    "pattern_summary": "stabilize-first pattern",
                    "extracted_from_episodes": ["2026-04-30T00:00:00Z"],
                    "confidence": 0.8,
                    "scope": {"scenario": "linux_runtime", "topic": "compatibility_release"},
                    "preferred_candidate_profiles": ["stabilize_first"],
                    "provenance": {
                        "source": "experience",
                        "provenance_detail": "stage_i_semantic_memory",
                        "confidence": 0.8,
                        "scope": {"scenario": "linux_runtime"},
                        "mutable": True,
                    },
                },
            )

            entries = read_semantic_memory(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["pattern_summary"], "stabilize-first pattern")


if __name__ == "__main__":
    unittest.main()
