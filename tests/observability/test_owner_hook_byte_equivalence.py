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

from eva.kernel import ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot, utc_now
from eva.l1_sensing.signal_bus import build_patrol_signals
from eva.l2_drive import DriveUpdatePolicy, build_default_drive_state, update_drive_state
from eva.observability import (
    RunIdentity,
    build_trace_sink,
    reset_current_trace,
    set_current_trace,
)
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


if __name__ == "__main__":
    unittest.main()
