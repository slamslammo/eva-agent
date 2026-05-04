from __future__ import annotations

import tempfile
import unittest

from eva.kernel import StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation.memory import (
    append_cognitive_memory_stub,
    append_habit_bias,
    append_learning_outcome,
    read_cognitive_memory_stub,
    read_habit_bias,
    read_learning_outcomes,
)


class EpisodicMemoryTests(unittest.TestCase):
    def test_append_and_read_cognitive_memory_stub_through_episodic_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            append_cognitive_memory_stub(
                store,
                {
                    "recorded_at": utc_now().isoformat(),
                    "source": "l3_deliberation",
                    "salience": 0.75,
                    "memory_type": "release_trace",
                    "write_reason": "release_outcome=compatibility_release",
                    "linked_audit_recorded_at": utc_now().isoformat(),
                    "content": {
                        "top_drive": "curiosity",
                        "release_outcome": "compatibility_release",
                        "drive_state_at_encoding": {
                            "top_drive": "curiosity",
                            "drive_levels": {"curiosity": 0.8},
                            "drive_trends": {"curiosity": "improving"},
                        },
                    },
                },
            )

            entries = read_cognitive_memory_stub(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["source"], "l3_deliberation")
            self.assertEqual(entries[0]["memory_type"], "release_trace")
            self.assertEqual(entries[0]["content"]["drive_state_at_encoding"]["top_drive"], "curiosity")

    def test_append_and_read_learning_outcomes_through_episodic_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            append_learning_outcome(
                store,
                {
                    "recorded_at": utc_now().isoformat(),
                    "source": "l3_learning",
                    "linked_audit_recorded_at": utc_now().isoformat(),
                    "expected_outcome": "stabilize_or_relieve_pressure",
                    "observed_outcome": "relieved",
                    "outcome_delta": 1.0,
                    "rpe_like_score": 1.0,
                    "evaluation_label": "positive",
                    "confidence": 0.9,
                    "content": {
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": True,
                        "habit_narrowed": True,
                    },
                },
            )

            entries = read_learning_outcomes(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["evaluation_label"], "positive")
            self.assertEqual(entries[0]["content"]["situation_key"], "integrity|STABLE|recent_yield_detected")

    def test_append_and_read_habit_bias_through_episodic_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            append_habit_bias(
                store,
                {
                    "recorded_at": utc_now().isoformat(),
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "stabilize_first",
                    "preferred_action": "shrink_to_conservative_mode",
                    "support_count": 2,
                    "failure_count": 0,
                    "last_outcome_delta": 1.0,
                    "bias_strength": 1.0,
                },
            )

            entries = read_habit_bias(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["candidate_profile"], "stabilize_first")
            self.assertEqual(entries[0]["bias_strength"], 1.0)


if __name__ == "__main__":
    unittest.main()
