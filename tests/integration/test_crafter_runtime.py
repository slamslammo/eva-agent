from __future__ import annotations

import json
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
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                summary = run_crafter_runtime(config)
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
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                run_crafter_runtime(config)
            store = StateStore(config.paths)
            response_history = store.read_response_history()
            self.assertGreaterEqual(len(stub_session.step_actions), 1)
            self.assertGreaterEqual(len(response_history), 1)
            self.assertIn(response_history[-1]["pressure_type"], {"safety", "metabolic", "recovery", "acquisition", "capability"})

    def test_widened_candidates_surface_in_runtime_response_history(self) -> None:
        """Round 1.A: at runtime, the bridge restricts widening to the
        candidate_profile L3 selected and produces a candidate_actions list
        that reflects context-driven widening. Without habit/prior bias the
        selected action is the first widened candidate (e.g., ``do`` rather
        than ``noop``), but the bridge's candidate_actions documents the
        wider set reaching runtime."""

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

            # The last response_history entry must record a non-trivial
            # candidate_actions list. Stage H pinned exactly 3 hardcoded
            # candidates regardless of pressure; Round 1.A makes the bridge
            # produce context-resolved candidates whose count and content
            # vary with the L3-chosen candidate_profile.
            last_response = response_history[-1]
            candidate_actions = last_response.get("candidate_actions")
            self.assertIsInstance(candidate_actions, list)
            self.assertGreaterEqual(
                len(candidate_actions),
                1,
                f"Bridge must produce at least one widened candidate; got {candidate_actions}",
            )

            # The selected action must always be one of the produced candidates.
            self.assertIn(
                last_response["selected_action"],
                candidate_actions,
                f"selected_action {last_response['selected_action']!r} must appear in candidate_actions {candidate_actions!r}",
            )

            # Profile-aware posture is carried into response_history through
            # selected_posture so traces can attribute the choice to a profile.
            selected_posture = last_response.get("selected_posture", "")
            self.assertTrue(
                any(selected_posture == token for token in (
                    "crafter_candidate_observe",
                    "crafter_candidate_stabilize",
                    "crafter_candidate_escalate",
                )),
                f"selected_posture must carry profile provenance after Round 1.A; got {selected_posture!r}",
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
            with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
                summary = run_crafter_runtime(config)
            # 个体终止收尾，而非 max_turns/max_runtime（substrate 被叫停）
            self.assertEqual(summary.exit_reason, "individual_terminated")
            self.assertGreaterEqual(len(stub_session.step_actions), 1)


class CrafterReasoningProposalIntegrationTests(unittest.TestCase):
    """Round 1.E — E-7: end-to-end, the model (as an anchor-bounded proposer) shapes
    the considered candidate set under llm_assisted and is inert under local_rule_based,
    while the mediator remains the sole release authority."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def _bounded_config(self, temp_dir: str, *, backend: str, model_client_mode: str | None = None):
        kwargs: dict[str, object] = {"working_memory_backend": backend}
        if model_client_mode is not None:
            kwargs["working_memory_model_client_mode"] = model_client_mode
        return build_runtime_config(
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
            **kwargs,
        )

    def _run_and_read_audits(self, config) -> list[dict]:
        stub_session = StubCrafterSession()
        with patch.object(CrafterRuntimeSession, "start", return_value=stub_session):
            run_crafter_runtime(config)
        return StateStore(config.paths).read_deliberation_audit()

    def test_llm_assisted_proposals_shape_considered_set_local_stays_inert(self) -> None:
        with tempfile.TemporaryDirectory() as llm_dir, tempfile.TemporaryDirectory() as local_dir:
            llm_audits = self._run_and_read_audits(
                self._bounded_config(llm_dir, backend="llm_assisted", model_client_mode="heuristic")
            )
            local_audits = self._run_and_read_audits(
                self._bounded_config(local_dir, backend="local_rule_based")
            )

            # llm_assisted: the model shaped the considered set → proposals recorded
            # in audit, with model_advisory provenance (demonstrable vs local).
            llm_with_proposals = [audit for audit in llm_audits if audit.get("proposals")]
            self.assertTrue(llm_with_proposals, "expected proposals recorded under llm_assisted")
            self.assertTrue(
                any(
                    proposal.get("provenance") == "model_advisory"
                    for audit in llm_with_proposals
                    for proposal in audit["proposals"]
                ),
                "expected at least one model_advisory proposal",
            )

            # local_rule_based: inert (proposer None) → behavior-preserving, no
            # proposals field appears in any audit record.
            self.assertFalse(
                any(audit.get("proposals") for audit in local_audits),
                "local_rule_based must stay inert (no proposals in audit)",
            )

            # §6 invariant end-to-end: the mediator remains the release authority —
            # every shaped pass still routes through a release_decision, and any
            # released action stays within the admitted candidate set.
            for audit in llm_with_proposals:
                self.assertIn("release_decision", audit)
                released = audit["release_decision"].get("selected_action")
                if released is not None:
                    admitted_actions = {candidate["action"] for candidate in audit["candidates"]}
                    self.assertIn(released, admitted_actions)


if __name__ == "__main__":
    unittest.main()
