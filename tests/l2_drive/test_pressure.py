from __future__ import annotations

import unittest
from datetime import timedelta

from eva.kernel import ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot, utc_now
from eva.l2_drive.pressure_to_drive import build_active_pressure_table
from scenarios.linux_runtime import activate_linux_runtime_scenario


class PressureTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_build_active_pressure_table_tracks_open_worsening_and_resolved_pressures(self) -> None:
        now = utc_now()
        empty_previous = ActivePressureTable(captured_at=now - timedelta(seconds=5))
        first_snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "disk_space_declining", "disk_free_bytes": 1024},
                )
            },
            overall_status="degraded",
            primary_gap={"type": "resource_state", "reason": "disk_space_declining"},
            trend="unknown",
            updated_at=now,
        )

        first_table, opened, resolved = build_active_pressure_table(first_snapshot, empty_previous)
        self.assertEqual(len(first_table.pressures), 1)
        self.assertEqual(len(opened), 1)
        self.assertEqual(len(resolved), 0)
        self.assertEqual(first_table.pressures[0].pressure_id, "pressure-linux_runtime-resource_state-disk_space_declining")
        self.assertEqual(first_table.pressures[0].trend, "unknown")

        second_snapshot = ExternalLifeSnapshot(
            captured_at=now + timedelta(seconds=10),
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(
                    status="critical",
                    evidence={"reason": "disk_space_declining", "disk_free_bytes": 256},
                )
            },
            overall_status="critical",
            primary_gap={"type": "resource_state", "reason": "disk_space_declining"},
            trend="worsening",
            updated_at=now + timedelta(seconds=10),
        )

        second_table, opened_again, resolved_again = build_active_pressure_table(second_snapshot, first_table)
        self.assertEqual(len(second_table.pressures), 1)
        self.assertEqual(len(opened_again), 0)
        self.assertEqual(len(resolved_again), 0)
        self.assertEqual(second_table.pressures[0].pressure_id, first_table.pressures[0].pressure_id)
        self.assertEqual(second_table.pressures[0].trend, "worsening")
        self.assertEqual(second_table.pressures[0].first_seen_at, first_table.pressures[0].first_seen_at)

        resolved_snapshot = ExternalLifeSnapshot(
            captured_at=now + timedelta(seconds=20),
            source_patrol="deep",
            dimensions={
                "resource_state": DimensionSnapshot(
                    status="healthy",
                    evidence={"reason": "resource_state_ok", "disk_free_bytes": 4096},
                )
            },
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="improving",
            updated_at=now + timedelta(seconds=20),
        )

        resolved_table, final_opened, final_resolved = build_active_pressure_table(resolved_snapshot, second_table)
        self.assertEqual(len(resolved_table.pressures), 0)
        self.assertEqual(len(final_opened), 0)
        self.assertEqual(len(final_resolved), 1)
        self.assertEqual(final_resolved[0].pressure_id, first_table.pressures[0].pressure_id)


if __name__ == "__main__":
    unittest.main()
