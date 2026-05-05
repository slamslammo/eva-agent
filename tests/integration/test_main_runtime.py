from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from eva.kernel import ExternalLifeConfig, LifecycleConfig, LoopControl, StateStore, build_runtime_config
from eva.l3_deliberation.memory import WorkingMemoryAdapterRequest, WorkingMemoryAdapterResponse
from eva.kernel.main import run_runtime


class CapturingRuntimeWorkingMemoryAdapter:
    def __init__(self) -> None:
        self.called = False
        self.request: WorkingMemoryAdapterRequest | None = None

    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        self.called = True
        self.request = request
        return WorkingMemoryAdapterResponse(
            candidate_suggestions=("observe_first",),
            prediction_hints=("bounded_runtime_hint",),
            reasoning_trace=("runtime_adapter_invoked",),
            confidence=0.62,
        )


class MainLoopTests(unittest.TestCase):
    def test_runtime_config_carries_working_memory_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir, working_memory_backend="auto")
            self.assertEqual(config.working_memory_backend, "auto")
            self.assertIsNone(config.working_memory_adapter)
            self.assertEqual(config.working_memory_adapter_mode, "inert")
            self.assertEqual(config.working_memory_model_client_mode, "inert")
            self.assertEqual(config.working_memory_model_client_config.provider, "placeholder")

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

    def test_bounded_run_generates_step1_patrol_artifacts_with_accelerated_cadence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=5, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            summary = run_runtime(config)
            self.assertGreaterEqual(summary.turns, 5)
            self.assertTrue(config.paths.external_life_snapshot_file.exists())
            self.assertTrue(config.paths.active_pressures_file.exists())
            self.assertTrue(config.paths.survival_log_file.exists())
            store = StateStore(config.paths)
            snapshot = store.read_external_life_snapshot()
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertIn(snapshot.source_patrol, {"shallow", "deep", "full"})
            self.assertIn(snapshot.overall_status, {"healthy", "degraded", "critical"})
            survival_log = store.read_survival_log()
            self.assertGreaterEqual(len(survival_log), 1)
            self.assertIn("survival_snapshot", [entry["event_type"] for entry in survival_log])
            patrol_turns = [
                event for event in store.read_events()
                if event["event_type"] == "turn_completed" and event["details"].get("work_kind") == "patrol"
            ]
            self.assertGreaterEqual(len(patrol_turns), 1)
            self.assertIn("signal_summary", patrol_turns[0]["details"])
            self.assertIn("signal_batch", patrol_turns[0]["details"])
            self.assertEqual(patrol_turns[0]["details"]["signal_batch"]["summary"], patrol_turns[0]["details"]["signal_summary"])
            self.assertIn("signal_routing", patrol_turns[0]["details"])
            self.assertIn("urgency", patrol_turns[0]["details"]["signal_routing"])
            self.assertIn("dispatch_hint", patrol_turns[0]["details"]["signal_routing"])
            self.assertGreaterEqual(patrol_turns[0]["details"]["signal_summary"]["signal_count"], 1)
            self.assertIn("drive_summary", patrol_turns[0]["details"])
            self.assertIn("top_drive", patrol_turns[0]["details"]["drive_summary"])
            self.assertIn("drive_broadcast", patrol_turns[0]["details"])
            self.assertIn("top_drive", patrol_turns[0]["details"]["drive_broadcast"])
            self.assertIn("runtime_gate_context", patrol_turns[0]["details"])
            self.assertIn("turn_allowed", patrol_turns[0]["details"]["runtime_gate_context"])
            self.assertIn("deliberation", patrol_turns[0]["details"])
            self.assertEqual(
                set(patrol_turns[0]["details"]["deliberation"].keys()),
                {"outcome", "selected_action", "selected_candidate_id", "habit_narrowed", "habit_narrowed_from", "release_authorized"},
            )
            if patrol_turns[0]["details"]["signal_routing"]["dispatch_hint"] == "protective_lane":
                self.assertIn("reflex", patrol_turns[0]["details"])
            self.assertIn("outcome", patrol_turns[0]["details"]["deliberation"])
            self.assertTrue(config.paths.deliberation_audit_file.exists())
            self.assertTrue(config.paths.cognitive_memory_stub_file.exists())
            memory_entries = store.read_cognitive_memory_stub()
            if memory_entries:
                self.assertIn("memory_type", memory_entries[0])
                self.assertIn("write_reason", memory_entries[0])
                self.assertIn("linked_audit_recorded_at", memory_entries[0])
                self.assertIsInstance(memory_entries[0].get("salience"), float)
                self.assertIn("drive_state_at_encoding", memory_entries[0].get("content", {}))

    def test_runtime_defaults_to_inert_null_adapter_for_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=3, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                working_memory_backend="llm_assisted",
            )
            run_runtime(config)
            audits = StateStore(config.paths).read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            self.assertEqual(working_memory_context["source_backend"], "llm_assisted")
            self.assertEqual(working_memory_context["advisory_source"], "client_backed_model_shell")
            self.assertEqual(working_memory_context["advisory_context"], {})

    def test_runtime_uses_explicit_working_memory_adapter_when_provided(self) -> None:
        adapter = CapturingRuntimeWorkingMemoryAdapter()
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=3, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                working_memory_backend="llm_assisted",
            )
            run_runtime(config, working_memory_adapter=adapter)
            audits = StateStore(config.paths).read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            self.assertEqual(working_memory_context["source_backend"], "llm_assisted")
            self.assertEqual(working_memory_context["advisory_source"], "explicit_adapter")
            self.assertEqual(
                working_memory_context["advisory_context"],
                {
                    "candidate_suggestions": ["observe_first"],
                    "prediction_hints": ["bounded_runtime_hint"],
                    "reasoning_trace": ["runtime_adapter_invoked"],
                    "confidence": 0.62,
                },
            )
            self.assertTrue(adapter.called)
            self.assertIsNotNone(adapter.request)
            assert adapter.request is not None
            self.assertEqual(adapter.request.situation_key, working_memory_context["situation_key"])

    def test_runtime_uses_builtin_heuristic_adapter_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=3, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                working_memory_backend="llm_assisted",
                working_memory_adapter_mode="heuristic",
            )
            run_runtime(config)
            audits = StateStore(config.paths).read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            self.assertEqual(working_memory_context["source_backend"], "llm_assisted")
            self.assertEqual(working_memory_context["advisory_source"], "builtin_heuristic_adapter")
            self.assertIn("candidate_suggestions", working_memory_context["advisory_context"])
            self.assertIn("prediction_hints", working_memory_context["advisory_context"])
            self.assertIn("reasoning_trace", working_memory_context["advisory_context"])

    def test_runtime_uses_heuristic_model_client_shell_for_llm_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=3, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                working_memory_backend="llm_assisted",
                working_memory_model_client_mode="heuristic",
            )
            run_runtime(config)
            audits = StateStore(config.paths).read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            advisory_context = working_memory_context["advisory_context"]
            self.assertEqual(working_memory_context["source_backend"], "llm_assisted")
            self.assertEqual(working_memory_context["advisory_source"], "client_backed_model_shell")
            self.assertEqual(advisory_context["candidate_suggestions"], ["observe_first"])
            self.assertIn("model_client_provider_heuristic", advisory_context["reasoning_trace"])
            self.assertIn("model_client_bounded-local-placeholder", advisory_context["reasoning_trace"])

    def test_cli_accepts_working_memory_backend_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eva.kernel.main",
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
                    "2",
                    "--max-runtime-sec",
                    "1",
                    "--idle-sleep-sec",
                    "0.01",
                    "--working-memory-backend",
                    "auto",
                    "--working-memory-adapter-mode",
                    "heuristic",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertIn("event=startup", result.stdout)
            self.assertTrue((Path(temp_dir) / "events.jsonl").exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eva.kernel.main",
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
                    "--working-memory-backend",
                    "llm_assisted",
                    "--working-memory-model-client-mode",
                    "heuristic",
                    "--working-memory-model-client-provider",
                    "cli-test-provider",
                    "--working-memory-model-client-model",
                    "cli-test-model",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertIn("event=startup", result.stdout)
            audits = StateStore(build_runtime_config(temp_dir).paths).read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            advisory_context = audits[0]["deliberation_input"]["working_memory_context"]["advisory_context"]
            self.assertIn("model_client_provider_cli-test-provider", advisory_context["reasoning_trace"])
            self.assertIn("model_client_cli-test-model", advisory_context["reasoning_trace"])

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "eva.kernel.main",
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
