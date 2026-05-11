from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from stability_metrics.metrics import calculate_stability_profile, write_stability_profile


class StabilityMetricsTests(unittest.TestCase):
    def test_calculate_stability_profile_from_synthetic_trace_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "deliberation_audit.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "recorded_at": "2026-05-11T00:00:00+00:00",
                                "deliberation_input": {
                                    "runtime_gate_context": {
                                        "instance_valid": True,
                                        "turn_allowed": True,
                                        "critical_blocked": False,
                                        "conservative_mode": False,
                                        "life_state": "STABLE",
                                    }
                                },
                                "release_decision": {"outcome": "compatibility_release"},
                            }
                        ),
                        json.dumps(
                            {
                                "recorded_at": "2026-05-11T00:01:00+00:00",
                                "deliberation_input": {
                                    "runtime_gate_context": {
                                        "instance_valid": True,
                                        "turn_allowed": False,
                                        "critical_blocked": True,
                                        "conservative_mode": False,
                                        "life_state": "CRITICAL",
                                    }
                                },
                                "release_decision": {"outcome": "compatibility_release"},
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "response_history.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "response_id": "resp-1",
                                "recorded_at": "2026-05-11T00:00:05+00:00",
                                "pressure_id": "p1",
                                "pressure_reason": "recent_yield_detected",
                                "selected_action": "recheck_runtime_integrity",
                                "pressure_outcome": "unknown",
                                "instance_valid": True,
                                "life_state": "STABLE",
                            }
                        ),
                        json.dumps(
                            {
                                "response_id": "resp-2",
                                "recorded_at": "2026-05-11T00:00:10+00:00",
                                "pressure_id": "p1",
                                "pressure_reason": "recent_yield_detected",
                                "selected_action": "shrink_to_conservative_mode",
                                "pressure_outcome": "relieved",
                                "instance_valid": True,
                                "life_state": "STABLE",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "learning_outcomes.jsonl").write_text(
                json.dumps(
                    {
                        "recorded_at": "2026-05-11T00:00:11+00:00",
                        "candidate_profile": "stabilize_first",
                        "outcome_delta": 1.0,
                        "evaluation_label": "positive",
                        "outcome_vector": {
                            "task_progress": None,
                            "viability_delta": {"level_1": 1.0},
                            "resource_delta": None,
                            "capability_delta": None,
                            "risk_delta": -1.0,
                            "reversibility": None,
                            "cost": None,
                            "uncertainty": 0.2,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "habit_bias.jsonl").write_text("", encoding="utf-8")

            profile = calculate_stability_profile(root)

            self.assertIn("metrics", profile)
            metrics = profile["metrics"]
            self.assertEqual(metrics["constraint_violation_rate"], 0.5)
            self.assertEqual(metrics["recovery_success_rate"], 1.0)
            self.assertEqual(metrics["mean_time_to_recovery_sec"], 5.0)
            self.assertEqual(metrics["useful_progress_under_constraint"], 1.0)
            self.assertEqual(metrics["cost_ratio"], 2.0)
            self.assertIsNotNone(metrics["recovery_path_entropy"])
            self.assertIsNotNone(metrics["continuity_preservation_score"])

    def test_write_stability_profile_persists_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "learning_outcomes.jsonl").write_text("", encoding="utf-8")
            output = write_stability_profile(root)
            self.assertTrue(output.exists())
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("metadata", payload)
            self.assertIn("metrics", payload)


if __name__ == "__main__":
    unittest.main()
