from __future__ import annotations

import tempfile
import unittest

from eva.kernel import StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation import build_deliberation_input, run_deliberation


class MemoryStubTests(unittest.TestCase):
    def test_run_deliberation_emits_no_memory_stub_without_threat_or_release(self) -> None:
        now = utc_now()
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )

        audit_record, memory_stub = run_deliberation(now, deliberation_input)

        self.assertEqual(audit_record.release_decision["outcome"], "withhold")
        self.assertIsNone(memory_stub)

    def test_run_deliberation_emits_memory_stub_payload(self) -> None:
        now = utc_now()
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )

        audit_record, memory_stub = run_deliberation(now, deliberation_input)

        self.assertEqual(audit_record.release_decision["outcome"], "compatibility_release")
        assert memory_stub is not None
        self.assertEqual(memory_stub["source"], "l3_deliberation")
        self.assertIsInstance(memory_stub["salience"], float)
        self.assertAlmostEqual(memory_stub["salience"], 0.75)
        self.assertEqual(memory_stub["memory_type"], "release_trace")
        self.assertEqual(memory_stub["write_reason"], "release_outcome=compatibility_release")
        self.assertEqual(memory_stub["linked_audit_recorded_at"], audit_record.recorded_at)
        self.assertEqual(memory_stub["content"]["top_drive"], "integrity")
        self.assertEqual(memory_stub["content"]["release_outcome"], "compatibility_release")
        self.assertEqual(memory_stub["content"]["selected_action"], "compatibility_release")
        self.assertEqual(memory_stub["content"]["candidate_profile"], "stabilize_first")
        self.assertEqual(
            memory_stub["content"]["drive_state_at_encoding"],
            {
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
        )

    def test_run_deliberation_keeps_full_audit_and_elevates_memory_on_threat(self) -> None:
        now = utc_now()
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
            pressure_table={"pressures": [{"pressure_id": "p1"}]},
        )

        audit_record, memory_stub = run_deliberation(now, deliberation_input)

        self.assertEqual(audit_record.release_decision["outcome"], "compatibility_release")
        self.assertEqual(audit_record.release_decision["selected_action"], "compatibility_release")
        self.assertEqual(
            audit_record.release_decision["release_context"],
            {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "stabilize_first",
                "bridge_policy": {
                    "policy_name": "stabilize_first_bias",
                    "selection": {
                        "preferred_action": "shrink_to_conservative_mode",
                        "fallback_action": "recheck_runtime_integrity",
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": True,
                    },
                },
            },
        )
        self.assertEqual(len(audit_record.candidates), 2)
        self.assertEqual(len(audit_record.assessments), 2)
        self.assertEqual(audit_record.deliberation_input["compatibility_pressure_table"]["pressures"][0]["pressure_id"], "p1")
        assert memory_stub is not None
        self.assertIsInstance(memory_stub["salience"], float)
        self.assertAlmostEqual(memory_stub["salience"], 0.95)
        self.assertEqual(memory_stub["memory_type"], "threat_trace")
        self.assertEqual(memory_stub["write_reason"], "threat_signal_present")
        self.assertEqual(memory_stub["linked_audit_recorded_at"], audit_record.recorded_at)
        self.assertEqual(memory_stub["content"]["top_drive"], "integrity")
        self.assertEqual(memory_stub["content"]["release_outcome"], "compatibility_release")
        self.assertEqual(memory_stub["content"]["selected_action"], "compatibility_release")
        self.assertEqual(memory_stub["content"]["candidate_profile"], "stabilize_first")
        self.assertEqual(
            memory_stub["content"]["drive_state_at_encoding"],
            {
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
        )
        self.assertNotIn("compatibility_pressure_table", memory_stub["content"])

    def test_memory_stub_persists_separately_from_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_deliberation_audit({"recorded_at": utc_now().isoformat(), "release_decision": {"outcome": "withhold"}})
            store.append_cognitive_memory_stub({
                "recorded_at": utc_now().isoformat(),
                "source": "l3_deliberation",
                "salience": 0.75,
                "memory_type": "release_trace",
                "write_reason": "release_outcome=compatibility_release",
                "linked_audit_recorded_at": utc_now().isoformat(),
                "content": {
                    "top_drive": "curiosity",
                    "release_outcome": "compatibility_release",
                    "drive_state_at_encoding": {
                        "top_drive": "curiosity",
                        "drive_levels": {"curiosity": 0.8},
                        "drive_trends": {"curiosity": "improving"},
                    },
                },
            })

            self.assertEqual(len(store.read_deliberation_audit()), 1)
            self.assertEqual(len(store.read_cognitive_memory_stub()), 1)
            self.assertFalse(store.paths.runtime_state_file.exists())


if __name__ == "__main__":
    unittest.main()
