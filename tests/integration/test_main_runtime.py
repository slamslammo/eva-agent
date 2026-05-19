from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from eva.kernel import AppendOnlyArtifactsConfig, ExternalLifeConfig, LifecycleConfig, LoopControl, StateStore, build_runtime_config
from eva.l1_sensing import SensorOutput, SensorSpec, build_sensor_registry
from eva.l3_deliberation.memory import WorkingMemoryAdapterRequest, WorkingMemoryAdapterResponse, WorkingMemoryModelClientConfig
from eva.kernel.main import run_runtime
from scenarios.linux_runtime import activate_linux_runtime_scenario


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


class FailingRuntimeWorkingMemoryAdapter:
    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        del request
        raise RuntimeError("anthropic_transport_unavailable")


class MainLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_runtime_config_carries_working_memory_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir, working_memory_backend="auto")
            self.assertEqual(config.working_memory_backend, "auto")
            self.assertIsNone(config.working_memory_adapter)
            self.assertEqual(config.working_memory_adapter_mode, "inert")
            # Round 1.7-c: default model client mode is "inert" (was "anthropic").
            # No external API call happens unless the user explicitly opts into
            # live mode via --working-memory-model-client-mode live + EVA_LLM_* env.
            self.assertEqual(config.working_memory_model_client_mode, "inert")
            self.assertEqual(config.working_memory_model_client_config.provider, "heuristic")
            self.assertEqual(config.working_memory_model_client_config.model, "bounded-local-placeholder")
            self.assertIsNone(config.append_only_artifacts.rotation_max_bytes)
            self.assertTrue(str(config.paths.append_only_archive_dir).endswith("archive"))

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
            self.assertIn("execution_lane", patrol_turns[0]["details"])
            if patrol_turns[0]["details"]["signal_routing"]["dispatch_hint"] == "protective_lane":
                self.assertIn("reflex", patrol_turns[0]["details"])
                self.assertEqual(patrol_turns[0]["details"]["execution_lane"], "fast")
                self.assertFalse(patrol_turns[0]["details"]["signal_routing"]["deliberation_allowed"])
                self.assertNotIn("deliberation", patrol_turns[0]["details"])
            else:
                self.assertIn("deliberation", patrol_turns[0]["details"])
                self.assertEqual(
                    set(patrol_turns[0]["details"]["deliberation"].keys()),
                    {"outcome", "selected_action", "selected_candidate_id", "habit_narrowed", "habit_narrowed_from", "release_authorized"},
                )
                self.assertIn("outcome", patrol_turns[0]["details"]["deliberation"])
            self.assertTrue(config.paths.deliberation_audit_file.exists() or patrol_turns[0]["details"]["execution_lane"] == "fast")
            self.assertTrue(config.paths.cognitive_memory_stub_file.exists())
            memory_entries = store.read_cognitive_memory_stub()
            if memory_entries:
                self.assertIn("memory_type", memory_entries[0])
                self.assertIn("write_reason", memory_entries[0])
                self.assertIn("linked_audit_recorded_at", memory_entries[0])
                self.assertIsInstance(memory_entries[0].get("salience"), float)
                self.assertIn("drive_state_at_encoding", memory_entries[0].get("content", {}))

    def test_bounded_run_rotates_append_only_tracks_when_threshold_is_low(self) -> None:
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
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
            )
            summary = run_runtime(config)
            self.assertGreaterEqual(summary.turns, 1)
            self.assertGreaterEqual(len(list(config.paths.append_only_archive_dir.glob("events.*.jsonl"))), 1)
            events = StateStore(config.paths).read_events()
            event_types = [event["event_type"] for event in events]
            self.assertIn("startup", event_types)
            self.assertIn("shutdown", event_types)

    def test_accelerated_run_reconstructs_complete_history_after_multiple_rotations(self) -> None:
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
                control=LoopControl(max_turns=8, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
            )
            summary = run_runtime(config)
            self.assertGreaterEqual(summary.turns, 8)
            store = StateStore(config.paths)
            events = store.read_events()
            self.assertEqual(events[0]["event_type"], "startup")
            self.assertEqual(events[-1]["event_type"], "shutdown")
            turn_events = [event for event in events if event["event_type"] == "turn_completed"]
            self.assertGreaterEqual(len(turn_events), 8)
            self.assertGreaterEqual(len(list(config.paths.append_only_archive_dir.glob("events.*.jsonl"))), 3)
            self.assertGreaterEqual(len(list(config.paths.append_only_archive_dir.glob("survival_log.*.jsonl"))), 1)
            self.assertIn("survival_snapshot", [entry["event_type"] for entry in store.read_survival_log()])

    def test_sequential_runs_preserve_history_and_increment_generation_after_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_first = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
            )
            first_summary = run_runtime(config_first)
            self.assertGreaterEqual(first_summary.turns, 1)
            store_after_first = StateStore(config_first.paths)
            active_after_first = store_after_first.read_active_instance()
            self.assertIsNotNone(active_after_first)
            assert active_after_first is not None

            config_second = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
            )
            second_summary = run_runtime(config_second)
            self.assertGreaterEqual(second_summary.turns, 1)
            store_after_second = StateStore(config_second.paths)
            active_after_second = store_after_second.read_active_instance()
            self.assertIsNotNone(active_after_second)
            assert active_after_second is not None
            self.assertEqual(active_after_second.generation, active_after_first.generation + 1)

            events = store_after_second.read_events()
            startup_generations = [event["generation"] for event in events if event["event_type"] == "startup"]
            shutdown_generations = [event["generation"] for event in events if event["event_type"] == "shutdown"]
            self.assertEqual(startup_generations, [active_after_first.generation, active_after_second.generation])
            self.assertEqual(shutdown_generations, [active_after_first.generation, active_after_second.generation])
            self.assertEqual(events[0]["event_type"], "startup")
            self.assertEqual(events[-1]["event_type"], "shutdown")
            self.assertGreaterEqual(len(list(config_second.paths.append_only_archive_dir.glob("events.*.jsonl"))), 2)
            self.assertIn("survival_snapshot", [entry["event_type"] for entry in store_after_second.read_survival_log()])

    def test_runtime_starts_with_preexisting_archives_across_mixed_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preload_config = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
                working_memory_backend="llm_assisted",
                working_memory_model_client_mode="heuristic",
            )
            preload_summary = run_runtime(preload_config)
            self.assertGreaterEqual(preload_summary.turns, 1)
            preload_store = StateStore(preload_config.paths, append_only_rotation_max_bytes=1)
            preload_store.append_response_history(
                {
                    "response_id": "resp-preexisting-1",
                    "recorded_at": "2026-05-06T10:00:01+00:00",
                    "selected_action": "recheck_runtime_integrity",
                    "pressure_outcome": "relieved",
                    "execution_status": "completed",
                    "followup_needed": False,
                    "drive_context": {"top_drive": "integrity", "drive_levels": {"integrity": 0.8}},
                    "life_state": "STABLE",
                    "pressure_reason": "recent_yield_detected",
                }
            )
            preload_store.append_response_history(
                {
                    "response_id": "resp-preexisting-2",
                    "recorded_at": "2026-05-06T10:00:02+00:00",
                    "selected_action": "shrink_to_conservative_mode",
                    "pressure_outcome": "unchanged",
                    "execution_status": "completed",
                    "followup_needed": False,
                    "drive_context": {"top_drive": "integrity", "drive_levels": {"integrity": 0.8}},
                    "life_state": "STABLE",
                    "pressure_reason": "recent_yield_detected",
                }
            )
            preload_store.append_learning_outcome(
                {
                    "recorded_at": "2026-05-06T10:00:03+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "observed_outcome": "relieved",
                    "evaluation_label": "positive",
                    "outcome_delta": 1.0,
                    "confidence": 0.9,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                }
            )
            preload_store.append_learning_outcome(
                {
                    "recorded_at": "2026-05-06T10:00:04+00:00",
                    "candidate_profile": "stabilize_first",
                    "selected_action": "shrink_to_conservative_mode",
                    "observed_outcome": "unchanged",
                    "evaluation_label": "neutral",
                    "outcome_delta": 0.0,
                    "confidence": 0.8,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                }
            )
            preload_store.append_habit_bias(
                {
                    "recorded_at": "2026-05-06T10:00:05+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 2,
                    "stability_score": 0.7,
                    "confidence": 0.6,
                    "bias_strength": 0.5,
                }
            )
            preload_store.append_habit_bias(
                {
                    "recorded_at": "2026-05-06T10:00:06+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 3,
                    "stability_score": 0.8,
                    "confidence": 0.9,
                    "bias_strength": 0.75,
                }
            )

            resumed_config = build_runtime_config(
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                append_only_artifacts=AppendOnlyArtifactsConfig(rotation_max_bytes=1),
                working_memory_backend="llm_assisted",
                working_memory_model_client_mode="heuristic",
            )
            resumed_summary = run_runtime(resumed_config)
            self.assertGreaterEqual(resumed_summary.turns, 1)
            resumed_store = StateStore(resumed_config.paths)

            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("events.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("survival_log.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("deliberation_audit.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("llm_advisory_audit.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("response_history.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("learning_outcomes.*.jsonl"))), 1)
            self.assertGreaterEqual(len(list(resumed_config.paths.append_only_archive_dir.glob("habit_bias.*.jsonl"))), 1)

            events = resumed_store.read_events()
            self.assertEqual(events[0]["event_type"], "startup")
            self.assertEqual(events[-1]["event_type"], "shutdown")
            self.assertGreaterEqual(sum(1 for event in events if event["event_type"] == "startup"), 2)
            self.assertGreaterEqual(sum(1 for event in events if event["event_type"] == "shutdown"), 2)
            self.assertIn("survival_snapshot", [entry["event_type"] for entry in resumed_store.read_survival_log()])
            self.assertIn("resp-preexisting-1", [entry.get("response_id") for entry in resumed_store.read_response_history()])
            self.assertIn("recheck_runtime_integrity", [entry["selected_action"] for entry in resumed_store.read_learning_outcomes()])
            self.assertIn("observe_first", [entry["candidate_profile"] for entry in resumed_store.read_habit_bias()])
            llm_audits = resumed_store.read_llm_advisory_audit()
            self.assertGreaterEqual(len(llm_audits), 1)
            self.assertIn(llm_audits[0]["outcome"], {"advisory_attached", "fallback_local"})

    def test_runtime_accepts_injected_sensor_registry(self) -> None:
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
            )
            registry = build_sensor_registry(
                (
                    SensorSpec(
                        name="host_continuity",
                        collect=lambda context: SensorOutput(
                            dimension="host_continuity",
                            payload={
                                "process_running": True,
                                "recent_restart_count": 0,
                                "schedule_drift_sec": 0.0,
                                "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
                            },
                        ),
                    ),
                    SensorSpec(
                        name="runtime_integrity",
                        collect=lambda context: SensorOutput(
                            dimension="runtime_integrity",
                            payload={
                                "instance_valid": True,
                                "runtime_writable": True,
                                "active_instance_present": True,
                                "runtime_state_present": True,
                                "events_present": True,
                                "lock_present": True,
                                "recent_yield_count": 0,
                                "recent_distress_count": 0,
                                "heartbeat_age_sec": context.runtime_state.heartbeat_age_sec,
                                "consecutive_failures": context.runtime_state.consecutive_failures,
                                "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
                            },
                        ),
                    ),
                    SensorSpec(
                        name="resource_state",
                        collect=lambda context: SensorOutput(
                            dimension="resource_state",
                            payload={
                                "runtime_path_exists": True,
                                "runtime_writable": True,
                                "disk_free_bytes": 10**10,
                                "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
                            },
                        ),
                    ),
                    SensorSpec(
                        name="anomaly_accumulation",
                        collect=lambda context: SensorOutput(
                            dimension="anomaly_accumulation",
                            payload={
                                "recent_error_count": 0,
                                "recent_yield_count": 0,
                                "recent_distress_count": 0,
                                "recent_restart_count": 0,
                                "anomaly_count": 0,
                                "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
                            },
                        ),
                    ),
                )
            )
            summary = run_runtime(config, sensor_registry=registry)
            self.assertGreaterEqual(summary.turns, 1)
            patrol_turns = [
                event for event in StateStore(config.paths).read_events()
                if event["event_type"] == "turn_completed" and event["details"].get("work_kind") == "patrol"
            ]
            self.assertGreaterEqual(len(patrol_turns), 1)
            self.assertEqual(patrol_turns[0]["details"]["signal_summary"]["status_signal_count"], 1)

    # Round 1.7-c removed the legacy
    # ``test_runtime_defaults_to_anthropic_client_shell_and_falls_back_locally_when_unavailable``
    # test. The default model client mode is now ``inert`` (no external call),
    # and the live-mode fallback-to-heuristic path is unit-tested at
    # ``tests/l3_deliberation/memory/test_openai_compatible_client.py``
    # (OpenAICompatibleRetryFallbackTests). Re-introducing an integration-level
    # version would duplicate that coverage without adding signal.

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
            store = StateStore(config.paths)
            audits = store.read_deliberation_audit()
            llm_audits = store.read_llm_advisory_audit()
            self.assertGreaterEqual(len(audits), 1)
            self.assertGreaterEqual(len(llm_audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            advisory_context = working_memory_context["advisory_context"]
            self.assertEqual(working_memory_context["source_backend"], "llm_assisted")
            self.assertEqual(working_memory_context["advisory_source"], "client_backed_model_shell")
            self.assertEqual(advisory_context["candidate_suggestions"], ["observe_first"])
            self.assertIn("model_client_provider_heuristic", advisory_context["reasoning_trace"])
            self.assertIn("model_client_bounded-local-placeholder", advisory_context["reasoning_trace"])
            self.assertEqual(llm_audits[0]["provider"], "heuristic")
            self.assertEqual(llm_audits[0]["outcome"], "advisory_attached")

    def test_runtime_fallback_writes_separate_llm_audit_without_changing_release_flow(self) -> None:
        adapter = FailingRuntimeWorkingMemoryAdapter()
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
            store = StateStore(config.paths)
            audits = store.read_deliberation_audit()
            llm_audits = store.read_llm_advisory_audit()
            self.assertGreaterEqual(len(audits), 1)
            self.assertGreaterEqual(len(llm_audits), 1)
            working_memory_context = audits[0]["deliberation_input"]["working_memory_context"]
            self.assertEqual(working_memory_context["source_backend"], "local_rule_based")
            self.assertEqual(working_memory_context["advisory_source"], "explicit_adapter:fallback")
            self.assertTrue(working_memory_context["advisory_fallback"])
            self.assertIn(audits[0]["release_decision"]["outcome"], {"released", "deferred", "withhold"})
            self.assertEqual(llm_audits[0]["outcome"], "fallback_local")
            self.assertEqual(llm_audits[0]["error"], "anthropic_transport_unavailable")

    def test_cli_accepts_working_memory_backend_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
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
            store = StateStore(build_runtime_config(temp_dir).paths)
            audits = store.read_deliberation_audit()
            llm_audits = store.read_llm_advisory_audit()
            self.assertGreaterEqual(len(audits), 1)
            self.assertGreaterEqual(len(llm_audits), 1)
            advisory_context = audits[0]["deliberation_input"]["working_memory_context"]["advisory_context"]
            self.assertIn("model_client_provider_cli-test-provider", advisory_context["reasoning_trace"])
            self.assertIn("model_client_cli-test-model", advisory_context["reasoning_trace"])
            self.assertEqual(llm_audits[0]["provider"], "cli-test-provider")
            self.assertEqual(llm_audits[0]["model"], "cli-test-model")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
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
                    "--append-only-rotation-max-bytes",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertIn("event=startup", result.stdout)
            self.assertGreaterEqual(len(list((Path(temp_dir) / "archive").glob("events.*.jsonl"))), 1)
            store = StateStore(build_runtime_config(temp_dir).paths)
            events = store.read_events()
            self.assertIn("startup", [event["event_type"] for event in events])
            self.assertIn("shutdown", [event["event_type"] for event in events])

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(__file__).resolve().parents[2]
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "runners.run_linux",
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
