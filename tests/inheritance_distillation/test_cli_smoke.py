from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InheritanceDistillationCliSmokeTests(unittest.TestCase):
    def test_cli_writes_bundle_from_synthetic_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "learning_outcomes.jsonl").write_text(
                "\n".join(
                    [
                        '{"recorded_at":"2026-05-16T00:00:00+00:00","selected_action":"sleep","candidate_profile":"stabilize_first","outcome_delta":1.0,"confidence":0.84,"content":{"scenario":"crafter","situation_key":"acquisition|RECOVERING|health_critical","candidate_profile":"stabilize_first"}}',
                        '{"recorded_at":"2026-05-16T00:01:00+00:00","selected_action":"sleep","candidate_profile":"stabilize_first","outcome_delta":0.7,"confidence":0.83,"content":{"scenario":"crafter","situation_key":"acquisition|RECOVERING|health_critical","candidate_profile":"stabilize_first"}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            subprocess.run(
                [sys.executable, "-m", "inheritance_distillation.cli", "distill", temp_dir],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertTrue((root / "DistilledPriorBundle.json").exists())


if __name__ == "__main__":
    unittest.main()
