from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.kernel import ActivePressure, ActivePressureTable, DriveState, DriveStateTable, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation import ReleaseToken
from eva.l3_deliberation.tool_edge import (
    build_integrity_response_candidates,
    build_response_selected_event_details,
    build_response_summary,
    filter_response_candidates,
    get_default_response_mode,
    maybe_respond_after_patrol,
    respond_to_integrity_pressure,
    select_integrity_response,
    select_response_action,
)
from eva.l2_drive.broadcast import build_drive_broadcast
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import (
    DEFAULT_RESPONSE_MODE,
    ESCALATE_ACTION,
    RECHECK_ACTION,
    REPAIR_ACTION,
    activate_linux_runtime_scenario,
)


class StubRuntime:
    def __init__(self) -> None:
        self.activated = False

    def activate_conservative_until_next_patrol(self) -> None:
        self.activated = True


class ResponseTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def _drive_broadcast(self) -> dict[str, object]:
        now = utc_now()
        table = DriveStateTable(
            captured_at=now,
            drives=[
                DriveState(drive_type="survival", level=0.1, updated_at=now),
                DriveState(drive_type="integrity", level=0.6, delta=0.2, trend="worsening", contributors=["runtime_integrity.recent_yield_detected"], updated_at=now),
                DriveState(drive_type="continuity", level=0.05, updated_at=now),
                DriveState(drive_type="curiosity", level=0.0, updated_at=now),
            ],
            updated_at=now,
        )
        return build_drive_broadcast(table).to_dict()

    def _pressure(self, reason: str, **evidence: object) -> ActivePressure:
        now = utc_now()
        base_evidence = {"reason": reason}
        base_evidence.update(evidence)
        return ActivePressure(
            pressure_id=f"pressure-integrity-{reason}",
            type="integrity",
            severity="critical",
            evidence=base_evidence,
            first_seen_at=now - timedelta(seconds=10),
            last_seen_at=now,
            trend="worsening",
            active=True,
        )

    def _state(self, life_state: str = "STABLE", *, instance_valid: bool = True) -> RuntimeState:
        return RuntimeState(life_state=life_state, instance_valid=instance_valid, heartbeat_ok=True, tick_ok=True)

    def _token(self, candidate_profile: str = "stabilize_first") -> ReleaseToken:
        candidate_id = f"candidate-compatibility-{candidate_profile.replace('_', '-')}"
        return ReleaseToken(
            token_id=f"release-token::{candidate_id}",
            outcome="compatibility_release",
            candidate_id=candidate_id,
            candidate_profile=candidate_profile,
        )

    def test_instance_invalid_defaults_to_recheck(self) -> None:
        pressure = self._pressure("instance_invalid")
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(pressure, state, candidates, decisions)

        self.assertEqual([candidate.action for candidate in candidates], [RECHECK_ACTION, ESCALATE_ACTION])
        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "best_information_gain")

    def test_runtime_files_missing_defaults_to_escalate(self) -> None:
        pressure = self._pressure("runtime_files_missing", runtime_state_present=False)
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(pressure, state, candidates, decisions)

        self.assertEqual(selection.selected_action, ESCALATE_ACTION)
        self.assertEqual(selection.selected_posture, "defer_or_request_help")

    def test_recent_yield_detected_in_stable_state_defaults_to_repair(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(pressure, state, candidates, decisions)

        self.assertEqual([candidate.action for candidate in candidates], [RECHECK_ACTION, REPAIR_ACTION, ESCALATE_ACTION])
        self.assertEqual(selection.selected_action, REPAIR_ACTION)
        self.assertEqual(selection.state_mode, "conservative")

    def test_recent_yield_detected_in_degraded_state_falls_back_to_escalate(self) -> None:
        pressure = self._pressure("recent_yield_detected")
        state = self._state("DEGRADED")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(pressure, state, candidates, decisions)

        self.assertEqual([candidate.action for candidate in candidates], [RECHECK_ACTION, ESCALATE_ACTION])
        self.assertEqual(selection.selected_action, ESCALATE_ACTION)

    def test_recent_yield_with_observe_first_biases_to_recheck(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "bridge_policy_bias")

    def test_recent_yield_with_bridge_policy_override_biases_to_recheck(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "bridge_policy_bias")

    def test_bridge_policy_fallback_selects_recheck_when_repair_is_denied(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=False,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": REPAIR_ACTION,
                    "fallback_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "bridge_policy_fallback")

    def test_non_applicable_bridge_policy_falls_back_to_pressure_default(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": RECHECK_ACTION,
                    "fallback_action": ESCALATE_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["instance_invalid"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, REPAIR_ACTION)
        self.assertEqual(selection.selected_action_reason, "state_requires_conservative_response")

    def test_recent_yield_with_stabilize_first_keeps_repair_preference(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)
        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": REPAIR_ACTION,
                    "fallback_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, REPAIR_ACTION)
        self.assertEqual(selection.selected_action_reason, "state_requires_conservative_response")

    def test_respond_to_integrity_pressure_writes_recheck_history_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            store.write_runtime_state(state)
            pressure = self._pressure("instance_invalid")
            store.write_active_pressures(
                ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)
            )
            store.paths.active_instance_file.write_text("{}\n", encoding="utf-8")
            store.paths.events_file.write_text('{"event_type": "startup"}\n', encoding="utf-8")

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertEqual(summary["response_mode"], DEFAULT_RESPONSE_MODE)
            self.assertEqual(summary["selected_action"], RECHECK_ACTION)
            self.assertEqual(summary["execution_status"], "completed")
            self.assertEqual(summary["pressure_outcome"], "unchanged")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["pressure_outcome"], "unchanged")
            self.assertEqual(history[0]["state_mode"], "normal")

    def test_respond_to_integrity_pressure_uses_observe_first_bridge_bias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            runtime = StubRuntime()
            release_context = {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "observe_first",
                "bridge_policy": {
                    "policy_name": "observe_first_bias",
                    "selection": {
                        "preferred_action": RECHECK_ACTION,
                        "fallback_action": ESCALATE_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                runtime=runtime,
                release_context=release_context,
                release_token=self._token("observe_first"),
                selected_candidate_id="candidate-compatibility-observe-first",
            )
            history = store.read_response_history()

            self.assertFalse(runtime.activated)
            self.assertEqual(summary["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["selected_action_reason"], "bridge_policy_bias")
            self.assertEqual(history[0]["release_context"], release_context)

    def test_respond_to_integrity_pressure_uses_escalate_first_profile_from_release_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure("runtime_files_missing", runtime_state_present=False)
            release_context = {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "escalate_first",
                "bridge_policy": {
                    "policy_name": "escalate_first_bias",
                    "selection": {
                        "preferred_action": ESCALATE_ACTION,
                        "fallback_action": RECHECK_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["runtime_files_missing", "runtime_not_writable", "recent_distress_detected"],
                        "life_states": ["RECOVERING", "STABLE", "DEGRADED", "CRITICAL"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                release_context=release_context,
                release_token=self._token("escalate_first"),
                selected_candidate_id="candidate-compatibility-escalate-first",
            )
            history = store.read_response_history()

            self.assertEqual(summary["selected_action"], ESCALATE_ACTION)
            self.assertEqual(summary["response_mode"], "pressure_led_compatibility")
            self.assertEqual(history[0]["selected_action"], ESCALATE_ACTION)
            self.assertEqual(history[0]["release_context"], release_context)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure("instance_invalid")
            store.write_active_pressures(
                ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)
            )
            store.paths.active_instance_file.write_text("{}\n", encoding="utf-8")
            store.paths.events_file.write_text('{"event_type": "startup"}\n', encoding="utf-8")
            release_context = {
                "bridge_target": "l2_reflex",
                "response_mode": "protective_reflex",
                "bridge_policy": {
                    "policy_name": "protective_recheck_first",
                    "selection": {
                        "preferred_action": RECHECK_ACTION,
                        "fallback_action": ESCALATE_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["instance_invalid"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                release_context=release_context,
                release_token=self._token("observe_first"),
                selected_candidate_id="candidate-compatibility-observe-first",
            )
            history = store.read_response_history()

            self.assertEqual(summary["response_mode"], "protective_reflex")
            self.assertEqual(summary["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["response_mode"], "protective_reflex")
            self.assertEqual(history[0]["release_context"], release_context)

    def test_observe_first_policy_blocks_repair_side_effects_even_if_repair_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            runtime = StubRuntime()
            release_context = {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "observe_first",
                "bridge_policy": {
                    "policy_name": "observe_first_bias",
                    "selection": {
                        "preferred_action": REPAIR_ACTION,
                        "fallback_action": RECHECK_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                runtime=runtime,
                release_context=release_context,
                release_token=self._token("observe_first"),
                selected_candidate_id="candidate-compatibility-observe-first",
            )
            history = store.read_response_history()

            self.assertFalse(runtime.activated)
            self.assertEqual(summary["selected_action"], REPAIR_ACTION)
            self.assertEqual(history[0]["selected_action"], REPAIR_ACTION)
            self.assertEqual(history[0]["side_effects"], [])
            self.assertEqual(history[0]["selected_action_reason"], "state_requires_conservative_response")

    def test_respond_to_integrity_pressure_writes_repair_history_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            runtime = StubRuntime()

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                runtime=runtime,
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertTrue(runtime.activated)
            self.assertEqual(summary["selected_action"], REPAIR_ACTION)
            self.assertEqual(summary["execution_status"], "completed")
            self.assertEqual(summary["pressure_outcome"], "unknown")
            self.assertEqual(history[0]["selected_action"], REPAIR_ACTION)
            self.assertEqual(history[0]["state_mode"], "conservative")
            self.assertEqual(history[0]["side_effects"], ["temporary_conservative_until_next_patrol"])
            self.assertTrue(history[0]["followup_needed"])

    def test_respond_to_integrity_pressure_writes_escalation_history_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure("runtime_files_missing", runtime_state_present=False)

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertEqual(summary["selected_action"], ESCALATE_ACTION)
            self.assertEqual(summary["execution_status"], "escalated")
            self.assertEqual(summary["pressure_outcome"], "unchanged")
            self.assertEqual(history[0]["selected_action"], ESCALATE_ACTION)
            self.assertEqual(history[0]["integration_hint"], "needs_human_review")

    def test_respond_to_integrity_pressure_records_broadcast_context_without_writing_drive_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure("instance_invalid")
            drive_context = self._drive_broadcast()
            release_context = {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "observe_first",
                "bridge_policy": {
                    "policy_name": "observe_first_bias",
                    "selection": {
                        "preferred_action": RECHECK_ACTION,
                        "fallback_action": ESCALATE_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = respond_to_integrity_pressure(
                store,
                pressure,
                state,
                now,
                drive_context=drive_context,
                release_context=release_context,
                release_token=self._token("observe_first"),
                selected_candidate_id="candidate-compatibility-observe-first",
            )
            history = store.read_response_history()

            self.assertEqual(summary["drive_context"], drive_context)
            self.assertEqual(summary["response_mode"], "pressure_led_compatibility")
            self.assertEqual(history[0]["drive_context"], drive_context)
            self.assertEqual(history[0]["response_mode"], "pressure_led_compatibility")
            self.assertEqual(history[0]["release_context"], release_context)
            self.assertIsNone(store.read_drive_state())

    def test_build_response_summary_returns_bounded_payload(self) -> None:
        pressure = self._pressure("instance_invalid")
        summary = build_response_summary(
            pressure,
            select_integrity_response(pressure, self._state("STABLE")),
            {
                "execution_status": "completed",
                "pressure_outcome": "unchanged",
                "followup_needed": True,
            },
            drive_context=self._drive_broadcast(),
            response_mode="protective_reflex",
        )

        self.assertEqual(summary["pressure_id"], pressure.pressure_id)
        self.assertEqual(summary["pressure_type"], "integrity")
        self.assertEqual(summary["response_mode"], "protective_reflex")
        self.assertEqual(summary["drive_context"]["top_drive"], "integrity")

    def test_build_response_selected_event_details_returns_minimal_payload(self) -> None:
        payload = build_response_selected_event_details(
            {
                "pressure_id": "pressure-integrity-instance_invalid",
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
                "selected_posture": "recheck_or_observe",
                "execution_status": "completed",
                "pressure_outcome": "unchanged",
                "followup_needed": True,
                "response_mode": "pressure_led_compatibility",
                "drive_context": self._drive_broadcast(),
            },
            work_slice="deep",
            work_kind="patrol",
        )

        self.assertEqual(
            payload,
            {
                "work_slice": "deep",
                "work_kind": "patrol",
                "pressure_id": "pressure-integrity-instance_invalid",
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
            },
        )

    def test_build_response_selected_event_details_includes_narrowing_metadata_when_present(self) -> None:
        payload = build_response_selected_event_details(
            {
                "pressure_id": "pressure-integrity-recent_yield_detected",
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
            },
            work_slice="deep",
            work_kind="patrol",
            selected_candidate_id="candidate-compatibility-observe-first",
            habit_narrowed=True,
            habit_narrowed_from=2,
        )

        self.assertEqual(
            payload,
            {
                "work_slice": "deep",
                "work_kind": "patrol",
                "pressure_id": "pressure-integrity-recent_yield_detected",
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
                "selected_candidate_id": "candidate-compatibility-observe-first",
                "habit_narrowed": True,
                "habit_narrowed_from": 2,
            },
        )

    def test_maybe_respond_after_patrol_returns_none_without_integrity_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            store.write_active_pressures(
                ActivePressureTable(
                    captured_at=now,
                    pressures=[
                        ActivePressure(
                            pressure_id="pressure-continuity-restart_loop",
                            type="continuity",
                            severity="critical",
                            evidence={"reason": "restart_loop"},
                            first_seen_at=now,
                            last_seen_at=now,
                            trend="worsening",
                            active=True,
                        )
                    ],
                    updated_at=now,
                )
            )

            summary = maybe_respond_after_patrol(store, state, now)

            self.assertIsNone(summary)
            self.assertEqual(store.read_response_history(), [])

    def test_maybe_respond_after_patrol_activates_runtime_for_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            store.write_active_pressures(
                ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)
            )
            runtime = StubRuntime()

            summary = maybe_respond_after_patrol(
                store,
                state,
                now,
                runtime=runtime,
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertTrue(runtime.activated)
            self.assertEqual(summary["selected_action"], REPAIR_ACTION)
            self.assertEqual(summary["response_mode"], "pressure_led_compatibility")
            self.assertEqual(history[0]["side_effects"], ["temporary_conservative_until_next_patrol"])

    def test_maybe_respond_after_patrol_uses_observe_first_profile_from_release_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            store.write_active_pressures(
                ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)
            )
            runtime = StubRuntime()
            release_context = {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "observe_first",
                "bridge_policy": {
                    "policy_name": "observe_first_bias",
                    "selection": {
                        "preferred_action": RECHECK_ACTION,
                        "fallback_action": ESCALATE_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": False,
                    },
                },
            }

            summary = maybe_respond_after_patrol(
                store,
                state,
                now,
                runtime=runtime,
                release_context=release_context,
                release_token=self._token("observe_first"),
                selected_candidate_id="candidate-compatibility-observe-first",
            )
            history = store.read_response_history()

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertFalse(runtime.activated)
            self.assertEqual(summary["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["selected_action"], RECHECK_ACTION)
            self.assertEqual(history[0]["selected_action_reason"], "bridge_policy_bias")

    def test_maybe_respond_after_patrol_remains_pressure_led_when_broadcast_top_drive_differs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            pressure = self._pressure(
                "recent_yield_detected",
                runtime_writable=True,
                active_instance_present=True,
                runtime_state_present=True,
                events_present=True,
                lock_present=True,
                recent_distress_count=0,
            )
            drive_context = build_drive_broadcast(
                DriveStateTable(
                    captured_at=now,
                    drives=[
                        DriveState(drive_type="survival", level=0.8, updated_at=now),
                        DriveState(drive_type="integrity", level=0.1, updated_at=now),
                        DriveState(drive_type="continuity", level=0.05, updated_at=now),
                        DriveState(drive_type="curiosity", level=0.0, updated_at=now),
                    ],
                    updated_at=now,
                )
            ).to_dict()
            store.write_active_pressures(
                ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)
            )

            summary = maybe_respond_after_patrol(
                store,
                state,
                now,
                drive_context=drive_context,
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary["selected_action"], REPAIR_ACTION)
            self.assertEqual(summary["response_mode"], "pressure_led_compatibility")
            self.assertEqual(summary["drive_context"]["top_drive"], "survival")
            self.assertEqual(history[0]["selected_action"], REPAIR_ACTION)
            self.assertEqual(history[0]["drive_context"]["top_drive"], "survival")

    def test_maybe_respond_after_patrol_selects_first_integrity_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = self._state("STABLE", instance_valid=True)
            first_integrity = self._pressure("runtime_files_missing", runtime_state_present=False)
            later_integrity = self._pressure("instance_invalid")
            store.write_active_pressures(
                ActivePressureTable(
                    captured_at=now,
                    pressures=[
                        ActivePressure(
                            pressure_id="pressure-continuity-restart_loop",
                            type="continuity",
                            severity="critical",
                            evidence={"reason": "restart_loop"},
                            first_seen_at=now,
                            last_seen_at=now,
                            trend="worsening",
                            active=True,
                        ),
                        first_integrity,
                        later_integrity,
                    ],
                    updated_at=now,
                )
            )

            summary = maybe_respond_after_patrol(
                store,
                state,
                now,
                drive_context=self._drive_broadcast(),
                release_token=self._token(),
                selected_candidate_id="candidate-compatibility-stabilize-first",
            )
            history = store.read_response_history()

            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary["pressure_id"], first_integrity.pressure_id)
            self.assertEqual(summary["selected_action"], ESCALATE_ACTION)
            self.assertEqual(summary["drive_context"]["top_drive"], "integrity")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["pressure_id"], first_integrity.pressure_id)
            self.assertEqual(history[0]["drive_context"]["top_drive"], "integrity")


if __name__ == "__main__":
    unittest.main()
