from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from inheritance_distillation.pipeline import distill_runtime_dirs
from inheritance_distillation.trace_io import infer_scenario, load_trace_bundle


class InheritanceDistillationTests(unittest.TestCase):
    def test_distill_runtime_dirs_builds_same_scenario_bundle_from_synthetic_crafter_traces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "learning_outcomes.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "recorded_at": "2026-05-16T00:00:00+00:00",
                                "linked_audit_recorded_at": "2026-05-16T00:00:00+00:00",
                                "selected_action": "sleep",
                                "candidate_profile": "stabilize_first",
                                "outcome_delta": 1.0,
                                "confidence": 0.84,
                                "content": {
                                    "scenario": "crafter",
                                    "top_drive": "acquisition",
                                    "life_state": "RECOVERING",
                                    "pressure_reason": "health_critical",
                                    "situation_key": "acquisition|RECOVERING|health_critical",
                                    "candidate_profile": "stabilize_first",
                                },
                            }
                        ),
                        json.dumps(
                            {
                                "recorded_at": "2026-05-16T00:01:00+00:00",
                                "linked_audit_recorded_at": "2026-05-16T00:01:00+00:00",
                                "selected_action": "sleep",
                                "candidate_profile": "stabilize_first",
                                "outcome_delta": 0.8,
                                "confidence": 0.81,
                                "content": {
                                    "scenario": "crafter",
                                    "top_drive": "acquisition",
                                    "life_state": "RECOVERING",
                                    "pressure_reason": "health_critical",
                                    "situation_key": "acquisition|RECOVERING|health_critical",
                                    "candidate_profile": "stabilize_first",
                                },
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "habit_bias.jsonl").write_text(
                json.dumps(
                    {
                        "recorded_at": "2026-05-16T00:01:05+00:00",
                        "situation_key": "acquisition|RECOVERING|health_critical",
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
                        "evidence_count": 4,
                        "stability_score": 0.8,
                        "confidence": 0.85,
                        "bias_strength": 0.7,
                        "provenance": {"scope": {"scenario": "crafter"}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "deliberation_audit.jsonl").write_text(
                json.dumps(
                    {
                        "recorded_at": "2026-05-16T00:00:00+00:00",
                        "deliberation_input": {
                            "working_memory_context": {
                                "situation_key": "acquisition|RECOVERING|health_critical"
                            }
                        },
                        "candidates": [
                            {
                                "candidate_id": "candidate-1",
                                "parameter_domain": {
                                    "candidate_profile": "stabilize_first",
                                    "habit_preferred_action": "sleep",
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            payload = distill_runtime_dirs([root])

            self.assertEqual(payload["scenario"], "crafter")
            self.assertGreaterEqual(payload["record_count"], 1)
            self.assertIn(str(root.resolve()), payload["source_runtime_dirs"])
            matching = [
                record
                for record in payload["records"]
                if record["content"].get("situation_key") == "acquisition|RECOVERING|health_critical"
                and record["content"].get("candidate_profile") == "stabilize_first"
            ]
            self.assertGreaterEqual(len(matching), 1)
            self.assertTrue(any(record["content"].get("preferred_action") == "sleep" for record in matching))

    def test_distill_runtime_dirs_rejects_cross_scenario_mix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_a = root / "runtime-a"
            runtime_b = root / "runtime-b"
            runtime_a.mkdir()
            runtime_b.mkdir()
            (runtime_a / "learning_outcomes.jsonl").write_text(
                json.dumps(
                    {
                        "content": {
                            "scenario": "crafter",
                            "situation_key": "acquisition|STABLE|inventory_sparse",
                            "candidate_profile": "observe_first",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (runtime_b / "learning_outcomes.jsonl").write_text(
                json.dumps(
                    {
                        "content": {
                            "scenario": "linux_runtime",
                            "situation_key": "integrity|STABLE|recent_yield_detected",
                            "candidate_profile": "observe_first",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exactly one scenario"):
                distill_runtime_dirs([runtime_a, runtime_b])

    def test_infer_scenario_reads_learning_content_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "learning_outcomes.jsonl").write_text(
                json.dumps(
                    {
                        "content": {
                            "scenario": "crafter",
                            "situation_key": "acquisition|STABLE|inventory_sparse",
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            bundle = load_trace_bundle(root)
            self.assertEqual(infer_scenario(bundle), "crafter")


if __name__ == "__main__":
    unittest.main()
