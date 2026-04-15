from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from eva.config import LifecycleConfig, LoopControl, build_runtime_config
from eva.main import run_runtime
from eva.state import StateStore


class MainLoopTests(unittest.TestCase):
    def test_bounded_run_creates_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(heartbeat_interval_sec=0.05, lease_duration_sec=0.2, recovering_window_sec=0.05),
                control=LoopControl(max_ticks=2, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            summary = run_runtime(config)
            self.assertEqual(summary.ticks, 2)
            self.assertTrue(config.paths.active_instance_file.exists())
            self.assertTrue(config.paths.runtime_state_file.exists())
            self.assertTrue(config.paths.events_file.exists())
            events = StateStore(config.paths).read_events()
            event_types = [event["event_type"] for event in events]
            self.assertIn("startup", event_types)
            self.assertIn("tick_completed", event_types)
            self.assertIn("shutdown", event_types)
            self.assertGreaterEqual(event_types.count("turn_completed"), 0)

    def test_bounded_run_executes_turns_when_guard_window_allows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                control=LoopControl(max_turns=2, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            summary = run_runtime(config)
            self.assertGreaterEqual(summary.turns, 2)
            self.assertLessEqual(summary.ticks, 2)
            events = StateStore(config.paths).read_events()
            completed_turns = [
                event
                for event in events
                if event["event_type"] == "turn_completed" and event["details"].get("status") == "completed"
            ]
            self.assertGreaterEqual(len(completed_turns), 2)

    def test_cli_bounded_run_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[1]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eva.main",
                    "--runtime-dir",
                    temp_dir,
                    "--heartbeat-interval",
                    "0.05",
                    "--lease-duration",
                    "0.2",
                    "--recovering-window",
                    "0.05",
                    "--max-ticks",
                    "2",
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
            self.assertIn("event=startup", result.stdout)
            self.assertIn("event=tick", result.stdout)
            self.assertIn("event=shutdown", result.stdout)
            self.assertIn("final_life_state=", result.stdout)
            self.assertTrue((Path(temp_dir) / "active_instance.json").exists())
            self.assertTrue((Path(temp_dir) / "runtime_state.json").exists())
            self.assertTrue((Path(temp_dir) / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
