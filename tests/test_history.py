from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.config import build_runtime_paths
from eva.history import build_survival_snapshot_entry, persist_patrol_artifacts
from eva.state import ActivePressure, ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot, StateStore, utc_now


class HistoryTests(unittest.TestCase):
    def test_build_survival_snapshot_entry_contains_summary_and_dimension_status(self) -> None:
        now = utc_now()
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "runtime_integrity": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "recent_yield_detected"},
                )
            },
            overall_status="degraded",
            primary_gap={"type": "runtime_integrity", "reason": "recent_yield_detected"},
            trend="stable",
            updated_at=now,
        )
        table = ActivePressureTable(captured_at=now, updated_at=now)

        entry = build_survival_snapshot_entry(snapshot, table)

        self.assertEqual(entry["event_type"], "survival_snapshot")
        self.assertEqual(entry["source_patrol"], "deep")
        self.assertEqual(entry["details"]["dimension_status"]["runtime_integrity"], "degraded")
        self.assertIn("runtime_integrity is recent_yield_detected", entry["details"]["summary"])

    def test_persist_patrol_artifacts_writes_current_state_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            snapshot = ExternalLifeSnapshot(
                captured_at=now,
                source_patrol="deep",
                dimensions={
                    "resource_state": DimensionSnapshot(
                        status="critical",
                        evidence={"reason": "disk_space_critical", "disk_free_bytes": 256},
                    )
                },
                overall_status="critical",
                primary_gap={"type": "resource_state", "reason": "disk_space_critical"},
                trend="worsening",
                updated_at=now,
            )
            pressure = ActivePressure(
                pressure_id="pressure-resource_state-disk_space_critical",
                type="resource_state",
                severity="critical",
                evidence={"reason": "disk_space_critical", "disk_free_bytes": 256},
                first_seen_at=now - timedelta(seconds=5),
                last_seen_at=now,
                trend="worsening",
                active=True,
            )
            table = ActivePressureTable(captured_at=now, pressures=[pressure], updated_at=now)

            persist_patrol_artifacts(
                store,
                snapshot,
                table,
                opened_pressures=[pressure],
                resolved_pressures=[],
                append_snapshot=True,
            )

            loaded_snapshot = store.read_external_life_snapshot()
            self.assertIsNotNone(loaded_snapshot)
            assert loaded_snapshot is not None
            self.assertEqual(loaded_snapshot.overall_status, "critical")
            self.assertEqual(store.read_active_pressures().pressures[0].pressure_id, pressure.pressure_id)

            survival_log = store.read_survival_log()
            self.assertEqual([entry["event_type"] for entry in survival_log], ["pressure_opened", "survival_snapshot"])

    def test_persist_patrol_artifacts_skips_snapshot_append_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            snapshot = ExternalLifeSnapshot(
                captured_at=now,
                source_patrol="shallow",
                dimensions={
                    "host_continuity": DimensionSnapshot(status="healthy", evidence={"reason": "host_continuity_ok"})
                },
                overall_status="healthy",
                primary_gap={"type": "none", "reason": "none"},
                trend="stable",
                updated_at=now,
            )
            table = ActivePressureTable(captured_at=now, pressures=[], updated_at=now)

            persist_patrol_artifacts(
                store,
                snapshot,
                table,
                opened_pressures=[],
                resolved_pressures=[],
                append_snapshot=False,
            )

            self.assertEqual(store.read_survival_log(), [])
            self.assertEqual(store.read_active_pressures().pressures, [])


if __name__ == "__main__":
    unittest.main()
