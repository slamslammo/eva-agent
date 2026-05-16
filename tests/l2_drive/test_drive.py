from __future__ import annotations

import unittest
from datetime import timedelta

from eva.kernel import ActivePressure, ActivePressureTable, DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot, utc_now
from eva.l1_sensing.signal_bus import build_patrol_signals, summarize_signal_dispatch
from eva.l2_drive import DriveUpdatePolicy, build_default_drive_state, build_drive_broadcast, update_drive_state


class DriveTests(unittest.TestCase):
    def test_update_drive_state_accumulates_risk_and_suppresses_curiosity(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(
                    status="critical",
                    evidence={"reason": "disk_space_critical", "rate_context": {"direction": "degrading"}},
                ),
                "runtime_integrity": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "recent_yield_detected", "rate_context": {"direction": "degrading"}},
                ),
                "host_continuity": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "restart_unstable", "rate_context": {"direction": "degrading"}},
                ),
                "anomaly_accumulation": DimensionSnapshot(
                    status="healthy",
                    evidence={"reason": "anomaly_window_quiet", "rate_context": {"direction": "stable"}},
                ),
            },
            overall_status="critical",
            primary_gap={"type": "resource_state", "reason": "disk_space_critical"},
            trend="worsening",
            updated_at=now,
        )
        signals = build_patrol_signals(snapshot, ActivePressureTable(captured_at=now))
        previous = build_default_drive_state(now - timedelta(seconds=10))

        table, summary = update_drive_state(previous, snapshot, signals)
        by_type = {drive.drive_type: drive for drive in table.drives}

        self.assertGreater(by_type["survival"].level, 0.0)
        self.assertGreater(by_type["integrity"].level, 0.0)
        self.assertGreater(by_type["continuity"].level, 0.0)
        self.assertEqual(by_type["curiosity"].level, 0.0)
        self.assertEqual(by_type["survival"].trend, "worsening")
        self.assertEqual(summary.top_drive, "survival")
        self.assertIn("survival", summary.changed_drives)

    def test_update_drive_state_recovers_curiosity_when_snapshot_is_healthy(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(status="healthy", evidence={"reason": "resource_state_ok"}),
                "runtime_integrity": DimensionSnapshot(status="healthy", evidence={"reason": "runtime_integrity_ok"}),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok"}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "anomaly_window_quiet"}),
            },
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="stable",
            updated_at=now,
        )
        previous = DriveStateTable(
            captured_at=now - timedelta(seconds=10),
            drives=[
                DriveState(drive_type="survival", level=0.3, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="integrity", level=0.2, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="continuity", level=0.1, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="curiosity", level=0.0, updated_at=now - timedelta(seconds=10)),
            ],
            updated_at=now - timedelta(seconds=10),
        )

        table, summary = update_drive_state(previous, snapshot, [])
        by_type = {drive.drive_type: drive for drive in table.drives}

        self.assertLess(by_type["survival"].level, 0.3)
        self.assertLess(by_type["integrity"].level, 0.2)
        self.assertLess(by_type["continuity"].level, 0.1)
        self.assertGreater(by_type["curiosity"].level, 0.0)
        self.assertEqual(by_type["curiosity"].trend, "worsening")
        self.assertIn("curiosity", summary.changed_drives)

    def test_update_drive_state_accepts_custom_policy_parameters(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(status="healthy", evidence={"reason": "resource_state_ok"}),
                "runtime_integrity": DimensionSnapshot(status="healthy", evidence={"reason": "runtime_integrity_ok"}),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok"}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "anomaly_window_quiet"}),
            },
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="stable",
            updated_at=now,
        )
        previous = DriveStateTable(
            captured_at=now - timedelta(seconds=10),
            drives=[
                DriveState(drive_type="survival", level=0.3, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="integrity", level=0.2, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="continuity", level=0.1, updated_at=now - timedelta(seconds=10)),
                DriveState(drive_type="curiosity", level=0.1, updated_at=now - timedelta(seconds=10)),
            ],
            updated_at=now - timedelta(seconds=10),
        )

        table, _ = update_drive_state(
            previous,
            snapshot,
            [],
            policy=DriveUpdatePolicy(base_decay=0.01, curiosity_recovery=0.15),
        )
        by_type = {drive.drive_type: drive for drive in table.drives}

        self.assertAlmostEqual(by_type["survival"].delta, -0.01)
        self.assertAlmostEqual(by_type["integrity"].delta, -0.01)
        self.assertAlmostEqual(by_type["continuity"].delta, -0.01)
        self.assertAlmostEqual(by_type["curiosity"].delta, 0.15)
        self.assertEqual(by_type["curiosity"].contributors, ["healthy_recovery"])

    def test_signal_publication_contract_reserves_background_without_emitting_it(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(status="healthy", evidence={"reason": "resource_state_ok", "rate_context": {"direction": "stable"}}),
                "runtime_integrity": DimensionSnapshot(status="degraded", evidence={"reason": "recent_yield_detected", "rate_context": {"direction": "degrading"}}),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok", "rate_context": {"direction": "stable"}}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "anomaly_window_quiet", "rate_context": {"direction": "stable"}}),
            },
            overall_status="degraded",
            primary_gap={"type": "runtime_integrity", "reason": "recent_yield_detected"},
            trend="worsening",
            updated_at=now,
        )
        pressure = ActivePressure(
            pressure_id="pressure-integrity-recent_yield_detected",
            type="integrity",
            severity="degraded",
            evidence={"reason": "recent_yield_detected", "rate_context": {"direction": "degrading"}},
            first_seen_at=now,
            last_seen_at=now,
            trend="worsening",
            active=True,
        )

        signals = build_patrol_signals(snapshot, ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now))
        payloads = [signal.to_dict() for signal in signals]
        summary = summarize_signal_dispatch(signals).to_dict()

        self.assertEqual([payload["class"] for payload in payloads], ["status", "threat"])
        self.assertEqual(payloads[0]["source"], "deep")
        self.assertIn("runtime_integrity", payloads[0]["rate_context"])
        self.assertEqual(payloads[1]["payload"]["pressure_id"], pressure.pressure_id)
        self.assertEqual(summary["signal_count"], 2)
        self.assertEqual(summary["status_signal_count"], 1)
        self.assertEqual(summary["threat_signal_count"], 1)
        self.assertEqual(summary["background_signal_count"], 0)
        self.assertTrue(summary["has_threat_signal"])

    def test_update_drive_state_accumulates_over_multiple_patrols(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(status="degraded", evidence={"reason": "disk_space_declining"}),
                "runtime_integrity": DimensionSnapshot(status="healthy", evidence={"reason": "runtime_integrity_ok"}),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok"}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "anomaly_window_quiet"}),
            },
            overall_status="degraded",
            primary_gap={"type": "resource_state", "reason": "disk_space_declining"},
            trend="worsening",
            updated_at=now,
        )
        pressure = ActivePressure(
            pressure_id="pressure-survival-disk_space_declining",
            type="survival",
            severity="degraded",
            evidence={"reason": "disk_space_declining"},
            first_seen_at=now,
            last_seen_at=now,
            trend="worsening",
            active=True,
        )
        first, _ = update_drive_state(
            build_default_drive_state(now - timedelta(seconds=5)),
            snapshot,
            build_patrol_signals(snapshot, ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)),
        )
        second, _ = update_drive_state(
            first,
            snapshot,
            build_patrol_signals(snapshot, ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)),
        )
        first_levels = {drive.drive_type: drive for drive in first.drives}
        second_levels = {drive.drive_type: drive for drive in second.drives}

        self.assertGreater(second_levels["survival"].level, first_levels["survival"].level)
        self.assertEqual(second_levels["survival"].trend, "worsening")
        self.assertEqual(second_levels["survival"].contributors, ["decay", "resource_state.disk_space_declining", "threat_signal_present"])
        self.assertEqual(second_levels["curiosity"].level, 0.0)
        self.assertEqual(second_levels["curiosity"].trend, "stable")

    def test_update_drive_state_recovers_curiosity_over_multiple_healthy_patrols(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(status="healthy", evidence={"reason": "resource_state_ok"}),
                "runtime_integrity": DimensionSnapshot(status="healthy", evidence={"reason": "runtime_integrity_ok"}),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok"}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={"reason": "anomaly_window_quiet"}),
            },
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="stable",
            updated_at=now,
        )
        first, _ = update_drive_state(
            DriveStateTable(
                captured_at=now - timedelta(seconds=10),
                drives=[
                    DriveState(drive_type="survival", level=0.3, updated_at=now - timedelta(seconds=10)),
                    DriveState(drive_type="integrity", level=0.2, updated_at=now - timedelta(seconds=10)),
                    DriveState(drive_type="continuity", level=0.1, updated_at=now - timedelta(seconds=10)),
                    DriveState(drive_type="curiosity", level=0.0, updated_at=now - timedelta(seconds=10)),
                ],
                updated_at=now - timedelta(seconds=10),
            ),
            snapshot,
            [],
        )
        second, _ = update_drive_state(first, snapshot, [])
        first_levels = {drive.drive_type: drive for drive in first.drives}
        second_levels = {drive.drive_type: drive for drive in second.drives}

        self.assertLess(second_levels["survival"].level, first_levels["survival"].level)
        self.assertLess(second_levels["integrity"].level, first_levels["integrity"].level)
        self.assertLess(second_levels["continuity"].level, first_levels["continuity"].level)
        self.assertGreater(second_levels["curiosity"].level, first_levels["curiosity"].level)
        self.assertEqual(second_levels["curiosity"].contributors, ["healthy_recovery"])

    def test_build_drive_broadcast_projects_read_only_surface(self) -> None:
        now = utc_now()
        table = DriveStateTable(
            captured_at=now,
            drives=[
                DriveState(drive_type="survival", level=0.4, delta=0.1, trend="worsening", contributors=["resource_state.disk_space_critical"], updated_at=now),
                DriveState(drive_type="integrity", level=0.2, delta=-0.05, trend="improving", contributors=["decay"], updated_at=now),
                DriveState(drive_type="continuity", level=0.1, delta=0.0, trend="stable", contributors=[], updated_at=now),
                DriveState(drive_type="curiosity", level=0.0, delta=-0.12, trend="improving", contributors=["threat_suppression"], updated_at=now),
            ],
            updated_at=now,
        )

        broadcast = build_drive_broadcast(table)
        payload = broadcast.to_dict()

        self.assertEqual(broadcast.top_drive, "survival")
        self.assertEqual(broadcast.top_level, 0.4)
        self.assertEqual(payload["drive_levels"]["survival"], 0.4)
        self.assertEqual(payload["drive_trends"]["survival"], "worsening")
        self.assertEqual(payload["drive_trends"]["integrity"], "improving")
        self.assertEqual(payload["drives"]["survival"]["delta"], 0.1)
        self.assertEqual(payload["drives"]["survival"]["trend"], "worsening")
        self.assertEqual(payload["drives"]["survival"]["contributors"], ["resource_state.disk_space_critical"])
        self.assertEqual(payload["drives"]["continuity"]["level"], 0.1)
        self.assertEqual(payload["captured_at"], table.to_dict()["captured_at"])
        self.assertEqual(payload["updated_at"], table.to_dict()["updated_at"])
        self.assertEqual({drive.drive_type: drive.level for drive in table.drives}, payload["drive_levels"])


if __name__ == "__main__":
    unittest.main()
