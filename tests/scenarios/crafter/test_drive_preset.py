from __future__ import annotations

import unittest
from datetime import timedelta

from eva.kernel import DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot, utc_now
from eva.l2_drive.drive_state import build_default_drive_state, update_drive_state
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET, DRIVE_TYPES


class CrafterDrivePresetTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_crafter_drive_preset_exposes_expected_drive_family(self) -> None:
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_types, DRIVE_TYPES)
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("avatar_metabolic"), "metabolic")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("avatar_safety"), "safety")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("avatar_recovery"), "recovery")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("inventory_acquisition"), "acquisition")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("inventory_capability"), "capability")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("local_view_threat"), "safety")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("local_view_resource"), "acquisition")
        self.assertEqual(CRAFTER_DRIVE_PRESET.drive_for_dimension("local_view_utility"), "capability")
        # Round 1.B-2: Crafter now opts into framework curiosity-style update
        # for its exploration drive.
        self.assertEqual(CRAFTER_DRIVE_PRESET.curiosity_drive_type, "exploration")

    def test_build_default_drive_state_uses_crafter_drive_types_after_activation(self) -> None:
        now = utc_now()
        table = build_default_drive_state(now)
        self.assertEqual(tuple(drive.drive_type for drive in table.drives), DRIVE_TYPES)

    def test_local_view_subsignals_raise_multiple_drives(self) -> None:
        now = utc_now()
        previous = DriveStateTable(
            captured_at=now - timedelta(seconds=10),
            drives=[DriveState(drive_type=drive_type, updated_at=now - timedelta(seconds=10)) for drive_type in DRIVE_TYPES],
            updated_at=now - timedelta(seconds=10),
        )
        snapshot = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "avatar_safety": DimensionSnapshot(
                    status="critical",
                    evidence={
                        "reason": "health_critical",
                        "status": "critical",
                        "threat_count": 2,
                        "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
                    },
                ),
                "avatar_metabolic": DimensionSnapshot(
                    status="healthy",
                    evidence={"reason": "metabolic_ok", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "avatar_recovery": DimensionSnapshot(
                    status="healthy",
                    evidence={"reason": "recovery_ok", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "inventory_acquisition": DimensionSnapshot(
                    status="healthy",
                    evidence={"reason": "inventory_ok", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "inventory_capability": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "tooling_missing", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "local_view_threat": DimensionSnapshot(
                    status="critical",
                    evidence={"reason": "threat_visible", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "local_view_resource": DimensionSnapshot(
                    status="critical",
                    evidence={"reason": "resource_visible", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
                "local_view_utility": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "utility_visible", "rate_context": {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}},
                ),
            },
            overall_status="critical",
            primary_gap={"type": "avatar_safety", "reason": "health_critical"},
            trend="worsening",
            updated_at=now,
        )
        table, summary = update_drive_state(previous, snapshot, [])
        by_type = {drive.drive_type: drive for drive in table.drives}
        self.assertGreater(by_type["safety"].level, 0.0)
        self.assertGreater(by_type["acquisition"].level, 0.0)
        self.assertGreater(by_type["capability"].level, 0.0)
        self.assertEqual(summary.top_drive, "safety")


if __name__ == "__main__":
    unittest.main()
