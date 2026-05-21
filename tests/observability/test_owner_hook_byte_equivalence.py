"""Round 1.H H-2c — l2.approach_delta owner-hook byte-equivalence (A condition c).

The flag-gated read-only hook inside drive_state._approach_target_delta must never
change the returned drive state: with the trace context off (default) vs an enabled
sink, update_drive_state must produce byte-identical DriveState rows. When enabled it
additionally emits l2.approach_delta carrying the current turn_index.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from eva.anchor import build_action_domain
from eva.kernel import ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot, utc_now
from eva.l1_sensing.signal_bus import build_patrol_signals
from eva.l2_drive import DriveUpdatePolicy, build_default_drive_state, update_drive_state
from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.reasoning import assess_candidates, build_candidates
from eva.observability import (
    RunIdentity,
    build_trace_sink,
    reset_current_trace,
    set_current_trace,
)
from scenarios.crafter import activate_crafter_scenario
from scenarios.linux_runtime import activate_linux_runtime_scenario

_APPROACH_POLICY = DriveUpdatePolicy(
    update_mode="approach",
    approach_rate=0.3,
    target_critical=0.9,
    target_degraded=0.55,
)


def _snapshot(now):
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol="deep",
        dimensions={
            "resource_state": DimensionSnapshot(status="critical", evidence={"reason": "resource_low"}),
            "runtime_integrity": DimensionSnapshot(status="degraded", evidence={"reason": "integrity_drift"}),
            "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_ok"}),
            "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "quiet"}),
        },
        overall_status="critical",
        primary_gap={"type": "resource_state", "reason": "resource_low"},
        trend="worsening",
        updated_at=now,
    )


def _rows(table):
    return [
        (d.drive_type, d.level, d.delta, d.trend, tuple(d.contributors))
        for d in table.drives
    ]


class ApproachDeltaOwnerHookTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()
        reset_current_trace()

    def tearDown(self) -> None:
        reset_current_trace()  # never leak an enabled current sink to other tests

    def test_owner_hook_is_byte_equivalent_and_emits_when_enabled(self) -> None:
        now = utc_now()
        snapshot = _snapshot(now)
        signals = build_patrol_signals(snapshot, ActivePressureTable(captured_at=now))
        previous = build_default_drive_state(now - timedelta(seconds=10))

        # Flag-off (default Null current trace).
        table_off, _ = update_drive_state(previous, snapshot, signals, policy=_APPROACH_POLICY)
        rows_off = _rows(table_off)

        # Flag-on (enabled sink as the current trace context).
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=True, identity=RunIdentity(run_id="r", individual_id="i"))
            set_current_trace(sink, 7)
            table_on, _ = update_drive_state(previous, snapshot, signals, policy=_APPROACH_POLICY)
            reset_current_trace()
            records = [
                json.loads(line)
                for line in (Path(tmp) / "cognitive_trace.jsonl").read_text().splitlines()
                if line.strip()
            ]

        # Read-only: returned drive state is byte-identical with the hook on vs off.
        self.assertEqual(rows_off, _rows(table_on))
        # Enabled: l2.approach_delta emitted, carrying the current turn_index.
        approach = [r for r in records if r.get("transform_id") == "l2.approach_delta"]
        self.assertGreaterEqual(len(approach), 1)
        self.assertEqual(approach[0]["turn_index"], 7)
        self.assertIn("target", approach[0]["outputs"])
        self.assertIn("delta", approach[0]["outputs"])


def _crafter_deliberation_input():
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0, "threat_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8, "metabolic": 0.5, "safety": 0.4,
                "recovery": 0.3, "capability": 0.6, "exploration": 0.1,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True, "turn_allowed": True, "critical_blocked": False,
            "conservative_mode": False, "life_state": "STABLE",
        },
    )


class CandidateScoringOwnerHookTests(unittest.TestCase):
    """H-3b: the candidate_scoring owner-hook in value_judgment.assess_candidates must
    not change the returned assessments (A condition c); enabled it emits one
    candidate_scoring snapshot per candidate carrying the score decomposition."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        reset_current_trace()

    def tearDown(self) -> None:
        reset_current_trace()

    def test_owner_hook_is_byte_equivalent_and_emits_when_enabled(self) -> None:
        di = _crafter_deliberation_input()
        candidates = build_candidates(build_action_domain(di))

        # Flag-off (default Null current trace).
        assess_off = assess_candidates(candidates, di)

        # Flag-on (enabled sink as the current trace context).
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=True, identity=RunIdentity(run_id="r", individual_id="i"))
            set_current_trace(sink, 3)
            assess_on = assess_candidates(candidates, di)
            reset_current_trace()
            records = [
                json.loads(line)
                for line in (Path(tmp) / "cognitive_trace.jsonl").read_text().splitlines()
                if line.strip()
            ]

        # Read-only: assessments identical with the hook off vs on.
        self.assertEqual(assess_off, assess_on)
        # Enabled: one candidate_scoring snapshot per candidate, with the decomposition.
        scoring = [r for r in records if r.get("snapshot_type") == "candidate_scoring"]
        self.assertEqual(len(scoring), len(candidates))
        self.assertEqual(scoring[0]["turn_index"], 3)
        for key in ("drive_weighted", "projection", "learning_bias", "habit", "advisory", "final_score"):
            self.assertIn(key, scoring[0]["values"])


if __name__ == "__main__":
    unittest.main()
