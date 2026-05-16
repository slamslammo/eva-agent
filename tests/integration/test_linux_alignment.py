from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eva.kernel import LoopControl, build_runtime_config
from eva.kernel.main import run_runtime
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE, activate_linux_runtime_scenario
from scenarios.linux_runtime.prior_skills import build_linux_runtime_startup_prior_registry
from stability_metrics.metrics import calculate_stability_profile, write_stability_profile


class LinuxScenarioAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_linux_runtime_bundle_aligns_with_stage_g_contracts(self) -> None:
        bundle = LINUX_RUNTIME_SCENARIO_BUNDLE
        self.assertEqual(bundle.name, "linux_runtime")
        self.assertEqual(bundle.anchors.observe_first_profile, "observe_first")
        self.assertEqual(bundle.anchors.stabilize_first_profile, "stabilize_first")
        self.assertEqual(bundle.anchors.escalate_first_profile, "escalate_first")
        self.assertEqual(bundle.outcome_observers.expected_outcome_for_release("compatibility_release", "stabilize_first"), "stabilize_or_relieve_pressure")
        self.assertEqual(bundle.prior_skills.habit_skill_match_for_candidate_profile("observe_first"), True)
        self.assertEqual(bundle.prior_skills.habit_skill_match_for_candidate_profile("unknown"), False)

    def test_linux_startup_prior_registry_is_explicit(self) -> None:
        registry = build_linux_runtime_startup_prior_registry()
        records = registry.records()
        self.assertGreaterEqual(len(records), 1)
        self.assertTrue(all(record.provenance.source == "scenario" for record in records))
        self.assertTrue(all(record.provenance.scope["scenario"] == "linux_runtime" for record in records))
        self.assertTrue(all("situation_key" in record.provenance.scope for record in records))

        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                control=LoopControl(max_turns=3, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            run_runtime(config)
            profile = calculate_stability_profile(temp_dir)
            write_stability_profile(temp_dir)
            self.assertIn("metrics", profile)
            self.assertIn("continuity_preservation_score", profile["metrics"])
            self.assertTrue((Path(temp_dir) / "stability_profile.json").exists())

    def test_linux_runtime_accepts_no_bundle_and_rejects_crafter_bundle(self) -> None:
        activate_linux_runtime_scenario(inherited_priors_path=None)
        bundle = {
            "scenario": "crafter",
            "records": [
                {
                    "confidence": 0.84,
                    "content": {
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "candidate_profile": "observe_first",
                        "preferred_action": "noop",
                        "evidence_count": 5,
                        "stability_score": 0.8,
                        "bias_strength": 0.6,
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "DistilledPriorBundle.json"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "linux_runtime"):
                activate_linux_runtime_scenario(inherited_priors_path=str(bundle_path))


if __name__ == "__main__":
    unittest.main()
