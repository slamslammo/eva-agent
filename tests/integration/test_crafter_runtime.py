from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eva.kernel import ExternalLifeConfig, LifecycleConfig, LoopControl, StateStore, build_runtime_config
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.wrapper import StepResult


class StubCrafterSession:
    def __init__(self) -> None:
        self.wrapper = None
        self.closed = False
        self.step_actions: list[str] = []
        self.latest_agent_observation = self._observation(health=2, wood=1, threat_count=1, achievements=[])

    @classmethod
    def start(cls, *, seed: int | None = None) -> "StubCrafterSession":
        del seed
        return cls()

    def _observation(self, *, health: int, wood: int, threat_count: int, achievements: list[str]) -> dict[str, object]:
        nearby = {"zombie": threat_count} if threat_count else {}
        return {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "episode-1",
            "step": 0,
            "visible": {
                "local_view": {
                    "nearby_objects": nearby,
                    "nearby_materials": {"tree": 1},
                },
                "life_panel": {"available": True, "values": {"health": health, "food": 9, "water": 9, "energy": 9}},
                "inventory_panel": {"available": True, "items": {"wood": wood}},
                "nearby_objects": ["zombie"] if threat_count else [],
            },
            "task_context": {
                "objective": "survive and unlock achievements",
                "unlocked_achievements_visible": achievements,
            },
            "available_actions": ["noop", "sleep", "do"],
            "notes": [],
        }

    def build_shared_facts(self) -> dict[str, object]:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str):
        self.step_actions.append(action_name)
        before = dict(self.latest_agent_observation)
        after = self._observation(health=3, wood=2, threat_count=0, achievements=["collect_wood"])
        self.latest_agent_observation = after
        return type(
            "CrafterActionStep",
            (),
            {
                "raw_observation": None,
                "reward": 1.0,
                "done": False,
                "raw_info": {},
                "agent_observation": after,
                "before_observation": before,
                "after_action_observation": after,
            },
        )()

    def close(self) -> None:
        self.closed = True


class CrafterRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_bounded_run_executes_crafter_patrol_and_response_with_shared_observation(self) -> None:
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            # PR-S1: bridge defers when no raw_action emerges → no env.step.
            # Inject a stub raw-action producer so the original test intent
            # ("at least one env.step happened") still holds under the new
            # deferred contract.
            from scenarios.crafter.reasoning import CrafterLLMActionProducer
            stub_producer = CrafterLLMActionProducer(
                chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "stub"}]}),
                observation_fn=lambda: stub_session.latest_agent_observation,
            )
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                summary = run_crafter_runtime(config, candidate_producer=stub_producer)
            self.assertGreaterEqual(summary.turns, 1)
            self.assertGreaterEqual(len(stub_session.step_actions), 1)
            store = StateStore(config.paths)
            snapshot = store.read_external_life_snapshot()
            assert snapshot is not None
            self.assertIn(
                snapshot.primary_gap["type"],
                {
                    "avatar_safety",
                    "avatar_metabolic",
                    "avatar_recovery",
                    "inventory_capability",
                    "inventory_acquisition",
                    "local_view_threat",
                    "local_view_resource",
                    "local_view_utility",
                },
            )
            self.assertGreaterEqual(len(store.read_response_history()), 1)
            response = store.read_response_history()[-1]
            self.assertIn("life_delta", response)
            self.assertIn("inventory_delta", response)
            self.assertIn("achievement_delta", response)
            self.assertIn("visible_threat_count", response)
            self.assertGreaterEqual(len(store.read_learning_outcomes()), 1)
            self.assertTrue(config.paths.events_file.exists())
            self.assertTrue(config.paths.learning_outcomes_file.exists())
            self.assertTrue(stub_session.closed)

    def test_bounded_run_releases_action_even_when_first_crafter_pressure_is_non_integrity(self) -> None:
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            # PR-S1: inject stub producer so env.step is invoked (vs new deferred default).
            from scenarios.crafter.reasoning import CrafterLLMActionProducer
            stub_producer = CrafterLLMActionProducer(
                chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "stub"}]}),
                observation_fn=lambda: stub_session.latest_agent_observation,
            )
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config, candidate_producer=stub_producer)
            store = StateStore(config.paths)
            response_history = store.read_response_history()
            self.assertGreaterEqual(len(stub_session.step_actions), 1)
            self.assertGreaterEqual(len(response_history), 1)
            self.assertIn(response_history[-1]["pressure_type"], {"safety", "metabolic", "recovery", "acquisition", "capability"})

    def test_bridge_defers_when_no_llm_producer(self) -> None:
        """PR-4: without a live LLM producer the bridge defers (fallback=defer).

        No raw-action candidates are produced → mediator may still release a
        heuristic candidate → bridge receives no action_hint → records
        crafter_bridge_defer_no_raw_action reason. The bridge never invents
        a baseline action (rev1 §6.3 red line).
        """

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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config)
            store = StateStore(config.paths)
            response_history = store.read_response_history()
            self.assertGreaterEqual(len(response_history), 1)

            # All heuristic-path (no LLM) bridge responses should be defer or raw_action_execution.
            for record in response_history:
                self.assertIn(
                    record.get("selected_action_reason"),
                    {"crafter_bridge_defer_no_raw_action", "crafter_raw_action_execution"},
                    f"Unexpected selection reason: {record.get('selected_action_reason')}",
                )

    def test_crafter_runtime_surfaces_loaded_inherited_priors_in_working_memory(self) -> None:
        bundle = {
            "scenario": "crafter",
            "distillation_date": "2026-05-15T00:00:00Z",
            "records": [
                {
                    "confidence": 0.84,
                    "content": {
                        "situation_key": "acquisition|RECOVERING|health_critical",
                        "candidate_profile": "stabilize_first",
                        "preferred_action": "sleep",
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
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
                inherited_priors_path=str(bundle_path),
            )
            stub_session = StubCrafterSession()
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config)
            store = StateStore(config.paths)
            audits = store.read_deliberation_audit()
            self.assertGreaterEqual(len(audits), 1)
            matching_audit = next(
                audit
                for audit in audits
                if audit["deliberation_input"]["working_memory_context"].get("situation_key") == "acquisition|RECOVERING|health_critical"
            )
            working_memory_context = matching_audit["deliberation_input"]["working_memory_context"]
            self.assertEqual(working_memory_context["source_backend"], "local_rule_based")
            self.assertEqual(len(working_memory_context["inherited_priors"]), 1)
            self.assertEqual(working_memory_context["inherited_priors"][0]["candidate_profile"], "stabilize_first")
            self.assertEqual(working_memory_context["inherited_priors"][0]["preferred_action"], "sleep")
            self.assertEqual(working_memory_context["inherited_priors"][0]["provenance"]["scope"]["scenario"], "crafter")
            self.assertEqual(working_memory_context["situation_key"], "acquisition|RECOVERING|health_critical")
            self.assertEqual(matching_audit["candidates"][0]["parameter_domain"]["candidate_profile"], "stabilize_first")
            self.assertEqual(matching_audit["candidates"][0]["parameter_domain"]["habit_hint_source"], "inherited_prior")
            self.assertIn("inherited_prior_hint", matching_audit["candidates"][0]["justification"])
            self.assertIn("inherited_prior_bias", matching_audit["assessments"][0]["bias_reasons"])
            self.assertTrue(config.paths.learning_outcomes_file.exists())



class CrafterTerminationSemanticsTests(unittest.TestCase):
    """v0.6 rev2：HP=0（env done）= 该 individual 真死 —— 不再 reset 续命；
    kernel 以 exit_reason='individual_terminated' 收尾本次 run（一个个体的一生）。"""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_session_terminates_on_done_without_reset(self) -> None:
        class _FakeWrapper:
            def __init__(self) -> None:
                self.reset_calls = 0
                self.step_calls = 0

            def reset(self, *, seed=None):
                self.reset_calls += 1
                return {"episode_id": "ep", "step": 0, "visible": {}}

            def step(self, action_name):
                self.step_calls += 1
                return StepResult(
                    raw_observation=None,
                    reward=0.0,
                    done=True,
                    raw_info={},
                    agent_observation={"episode_id": "ep", "step": 1, "visible": {"dead": True}},
                )

            def close(self) -> None:
                pass

        wrapper = _FakeWrapper()
        session = CrafterRuntimeSession(
            wrapper=wrapper,
            latest_agent_observation={"episode_id": "ep", "step": 0, "visible": {}},
        )
        self.assertFalse(session.terminated)
        step = session.step_action("do")
        self.assertTrue(step.done)
        self.assertTrue(session.terminated)          # 个体终止标志置位
        self.assertEqual(wrapper.reset_calls, 0)     # 不再 reset 续命
        # 保留终止时的 observation（不是 reset 后的新局观测）
        self.assertEqual(session.latest_agent_observation["visible"], {"dead": True})

    def test_run_ends_with_individual_terminated_when_session_reports_terminated(self) -> None:
        class _TerminatingStub(StubCrafterSession):
            def step_action(self, action_name):
                result = super().step_action(action_name)
                self.terminated = True  # 第一步后即个体终止
                return result

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
                control=LoopControl(max_turns=50, max_runtime_sec=3.0, idle_sleep_sec=0.01),
            )
            stub_session = _TerminatingStub()
            # PR-S1: termination requires env.step to be invoked; inject stub
            # producer so the bridge emits a raw action (not deferred).
            from scenarios.crafter.reasoning import CrafterLLMActionProducer
            stub_producer = CrafterLLMActionProducer(
                chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "stub"}]}),
                observation_fn=lambda: stub_session.latest_agent_observation,
            )
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                summary = run_crafter_runtime(config, candidate_producer=stub_producer)
            # 个体终止收尾，而非 max_turns/max_runtime（substrate 被叫停）
            self.assertEqual(summary.exit_reason, "individual_terminated")
            self.assertGreaterEqual(len(stub_session.step_actions), 1)


class CrafterRawActionProducerWiringIntegrationTests(unittest.TestCase):
    """PR-4: end-to-end raw-action path with a stub CrafterLLMActionProducer.

    Proves CrafterLLMActionProducer -> run_deliberation threading ->
    release_context["action_hint"] -> Crafter bridge -> executed action.
    """

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_raw_action_producer_drives_executed_action(self) -> None:
        from scenarios.crafter.reasoning import CrafterLLMActionProducer

        chosen_action = "move_left"

        def stub_chat(messages):
            return json.dumps({"candidates": [{"action": chosen_action, "reason": "go left"}]})

        observation = {
            "visible": {
                "life_panel": {"available": True, "values": {"health": 5, "food": 5, "water": 5, "energy": 5}},
                "inventory_panel": {"available": True, "items": {}},
                "local_view": {"nearby_objects": {}, "cells": [["grass"] * 9] * 7, "center": {"row": 3, "col": 4}},
                "facing": "left",
            },
        }

        producer = CrafterLLMActionProducer(
            chat_fn=stub_chat,
            observation_fn=lambda: observation,
        )

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
                control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config, candidate_producer=producer)
            store = StateStore(config.paths)
            response_history = store.read_response_history()

        raw_executed = [
            r for r in response_history
            if r.get("selected_action_reason") == "crafter_raw_action_execution"
        ]
        # At least one raw-action execution must surface in response history.
        self.assertGreaterEqual(len(raw_executed), 1)
        for record in raw_executed:
            self.assertEqual(record.get("selected_action"), chosen_action)


class CrafterP1aTraceIntegrationTests(unittest.TestCase):
    """Round 1.H H-2a: under EVA_TRACE=1 the slow-lane seam emits the P1a batch-1
    transforms (l1.signal_publish / l2.broadcast / anchor.admit + drive_state
    snapshot), aligned by turn_index, with run_meta written. 0-token (stub)."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_eva_trace_emits_p1a_batch1_seam_events(self) -> None:
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
                control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
            )
            stub_session = StubCrafterSession()
            with patch.dict(os.environ, {"EVA_TRACE": "1"}), patch.object(
                CrafterRuntimeSession, "start", return_value=stub_session
            ):
                run_crafter_runtime(config)
            runtime_dir = Path(config.paths.runtime_dir)
            self.assertTrue((runtime_dir / "run_meta.json").exists())
            trace_path = runtime_dir / "cognitive_trace.jsonl"
            self.assertTrue(trace_path.exists())
            records = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
            self.assertGreaterEqual(len(records), 4)
            transform_ids = {r["transform_id"] for r in records if r["event_type"] == "transform"}
            self.assertIn("l1.signal_publish", transform_ids)
            self.assertIn("l2.broadcast", transform_ids)
            self.assertIn("anchor.admit", transform_ids)
            self.assertIn("l1.raw_observation", transform_ids)  # H-2b
            self.assertIn("l2.approach_delta", transform_ids)  # H-2c owner-hook
            self.assertIn("l1.threshold_classify", transform_ids)  # H-2d
            # H-3a: P1b batch-2 L3 chain.
            self.assertIn("l3.candidate_produce", transform_ids)
            self.assertIn("l3.assess_score", transform_ids)
            self.assertIn("l3.decide_release", transform_ids)
            self.assertIn("mediator.release", transform_ids)
            self.assertIn("bridge.resolve_action", transform_ids)
            # round-1i I-2: bridge.resolve_action now carries a non-None
            # selected_action_reason (trace-gap fix; was None before).
            bridge_events = [r for r in records if r.get("transform_id") == "bridge.resolve_action"]
            self.assertTrue(all(b["outputs"].get("selected_action_reason") for b in bridge_events))
            snapshot_types = {r["snapshot_type"] for r in records if r["event_type"] == "snapshot"}
            self.assertIn("drive_state", snapshot_types)
            self.assertIn("candidate_scoring", snapshot_types)  # H-3b owner-hook #2
            # H-2b: raw observation grid persisted under raw_observations/.
            raw_files = list((runtime_dir / "raw_observations").glob("turn-*.json"))
            self.assertGreaterEqual(len(raw_files), 1)
            # Every event carries the common envelope + a turn_index.
            for record in records:
                self.assertIn("run_id", record)
                self.assertIsInstance(record["turn_index"], int)
            # The first deliberating turn's events share one turn_index (aligned replay).
            first_turn = [r for r in records if r["turn_index"] == 0]
            self.assertTrue(any(r.get("transform_id") == "anchor.admit" for r in first_turn))

    def test_full_chain_schema_conformance_and_replay(self) -> None:
        """Round 1.H H-4: a traced run is schema-conformant and replayable — every
        event satisfies the §2 envelope + §3/§4 shape, turn_index is monotonic, and
        run_meta §1 is fully populated. 0-token (stub)."""

        envelope_keys = {
            "run_id", "individual_id", "individual_boundary", "continuity_state",
            "inherited_from", "episode_step", "turn_index", "event_type", "ts",
        }
        valid_layers = {"L1", "L2", "L3", "anchor", "mediator", "bridge", "kernel"}
        valid_continuity = {"alive", "terminated", "new_individual", "inherited"}
        valid_edges = {
            "top_drive_bias", "pressure", "habit_override", "inherited_prior",
            "llm_advisory", "projection_fallback", "drive_floor",
        }
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
                control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
            )
            with patch.dict(os.environ, {"EVA_TRACE": "1"}), patch.object(
                CrafterRuntimeSession, "start", return_value=StubCrafterSession()
            ):
                run_crafter_runtime(config)
            runtime_dir = Path(config.paths.runtime_dir)
            meta = json.loads((runtime_dir / "run_meta.json").read_text())
            records = [
                json.loads(line)
                for line in (runtime_dir / "cognitive_trace.jsonl").read_text().splitlines()
                if line.strip()
            ]

        # run_meta §1 fully populated.
        for key in ("run_id", "scenario", "memory_backend", "candidate_producer_version", "anchor_policy", "started_at"):
            self.assertTrue(meta.get(key), key)
        for key in ("reset_semantics", "clock_source", "individual_boundary", "inheritance_channel"):
            self.assertIn(key, meta["existence_semantics"])

        # Every event is envelope-conformant and turn_index is monotonic non-decreasing.
        last_turn = -1
        emitted_ids: set[str] = set()
        for record in records:
            self.assertTrue(envelope_keys.issubset(record), record.get("transform_id") or record.get("snapshot_type"))
            self.assertIn(record["continuity_state"], valid_continuity)
            self.assertGreaterEqual(record["turn_index"], last_turn)
            last_turn = record["turn_index"]
            if record["event_type"] == "transform":
                self.assertIn(record["layer"], valid_layers)
                self.assertTrue(record["transform_id"])
                self.assertTrue(record["code_anchor"])
                self.assertIsInstance(record["parents"], list)
                for parent in record["parents"]:
                    self.assertIn("id", parent)
                    self.assertIn(parent["edge_type"], valid_edges)
                emitted_ids.add(record["transform_id"])
            else:
                self.assertEqual(record["event_type"], "snapshot")
                self.assertTrue(record["snapshot_type"])
                self.assertIsInstance(record["values"], dict)

        # Chain connectivity: non-root parents reference transform_ids actually emitted.
        for record in records:
            if record["event_type"] != "transform":
                continue
            for parent in record["parents"]:
                self.assertIn(parent["id"], emitted_ids)


if __name__ == "__main__":
    unittest.main()
