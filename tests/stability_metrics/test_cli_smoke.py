from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class StabilityMetricsCliSmokeTests(unittest.TestCase):
    def test_cli_writes_profile_from_linux_runtime_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "runners.run_linux",
                    "--runtime-dir",
                    temp_dir,
                    "--heartbeat-interval",
                    "0.2",
                    "--lease-duration",
                    "1.0",
                    "--recovering-window",
                    "0.05",
                    "--turn-guard-window",
                    "0.01",
                    "--shallow-patrol-interval",
                    "0.01",
                    "--deep-patrol-interval",
                    "0.02",
                    "--full-report-interval",
                    "0.03",
                    "--recent-event-window",
                    "60",
                    "--max-turns",
                    "3",
                    "--max-runtime-sec",
                    "1",
                    "--idle-sleep-sec",
                    "0.01",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            subprocess.run(
                [sys.executable, "-m", "stability_metrics", "calculate", temp_dir],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertTrue((Path(temp_dir) / "stability_profile.json").exists())


if __name__ == "__main__":
    unittest.main()
