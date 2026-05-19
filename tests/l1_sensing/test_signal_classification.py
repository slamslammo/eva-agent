"""Round 1.B-4: pin signal-classification semantics.

Pre-1.B-4 behavior: ``build_patrol_signals`` indiscriminately emitted
``class="threat"`` for every active pressure, regardless of whether the
pressure was an imminent danger (zombie / runtime-integrity violation) or
an ongoing optimization pressure (resource scarcity / capability gap /
metabolic decay). Downstream consumers treating ``class="threat"`` as
"there is a real danger" therefore mis-fired whenever any pressure was
active — pinning exploration drive at 0 in Crafter and amplifying memory
salience inappropriately.

Post-1.B-4 behavior: scenarios declare ``imminent_threat_pressure_types``
on their ``SensorPolicyBundle``. Pressures of those types emit
``class="threat"``; all other pressures emit ``class="pressure"``.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from eva.kernel import ActivePressure, ActivePressureTable, DimensionSnapshot, ExternalLifeSnapshot
from eva.l1_sensing.signal_bus import build_patrol_signals, summarize_signal_dispatch
from scenarios.crafter import activate_crafter_scenario
from scenarios.linux_runtime import activate_linux_runtime_scenario


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _make_pressure(type_: str, reason: str) -> ActivePressure:
    now = _utc_now()
    return ActivePressure(
        pressure_id=f"pressure-{type_}-{reason}",
        type=type_,
        severity="degraded",
        evidence={"reason": reason},
        first_seen_at=now,
        last_seen_at=now,
        trend="worsening",
        active=True,
    )


def _make_minimal_snapshot() -> ExternalLifeSnapshot:
    now = _utc_now()
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol="deep",
        dimensions={
            "avatar_metabolic": DimensionSnapshot(status="healthy", evidence={"reason": "ok"}),
        },
        overall_status="healthy",
        primary_gap={"type": "none", "reason": "none"},
        trend="stable",
        updated_at=now,
    )


class CrafterImminentVsPressureSignalsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_safety_pressure_emits_threat_class(self) -> None:
        snapshot = _make_minimal_snapshot()
        pressure_table = ActivePressureTable(
            captured_at=snapshot.captured_at,
            pressures=[_make_pressure("safety", "threat_visible")],
            updated_at=snapshot.captured_at,
        )
        signals = build_patrol_signals(snapshot, pressure_table)
        threat_signals = [s for s in signals if s.signal_class == "threat"]
        pressure_signals = [s for s in signals if s.signal_class == "pressure"]
        self.assertEqual(len(threat_signals), 1)
        self.assertEqual(len(pressure_signals), 0)

    def test_acquisition_pressure_emits_pressure_class_not_threat(self) -> None:
        """The bug that motivated Round 1.B-4: pre-fix this would emit
        ``class="threat"``, fooling routing / curiosity suppression / memory
        salience into treating an "I see a tree" pressure as a real danger."""

        snapshot = _make_minimal_snapshot()
        pressure_table = ActivePressureTable(
            captured_at=snapshot.captured_at,
            pressures=[_make_pressure("acquisition", "resource_visible")],
            updated_at=snapshot.captured_at,
        )
        signals = build_patrol_signals(snapshot, pressure_table)
        threat_signals = [s for s in signals if s.signal_class == "threat"]
        pressure_signals = [s for s in signals if s.signal_class == "pressure"]
        self.assertEqual(len(threat_signals), 0)
        self.assertEqual(len(pressure_signals), 1)
        self.assertEqual(pressure_signals[0].payload.get("type"), "acquisition")

    def test_mixed_pressures_split_by_imminence(self) -> None:
        snapshot = _make_minimal_snapshot()
        pressure_table = ActivePressureTable(
            captured_at=snapshot.captured_at,
            pressures=[
                _make_pressure("safety", "threat_visible"),
                _make_pressure("metabolic", "food_low"),
                _make_pressure("capability", "tooling_missing"),
                _make_pressure("acquisition", "resource_visible"),
            ],
            updated_at=snapshot.captured_at,
        )
        signals = build_patrol_signals(snapshot, pressure_table)
        threat_signals = [s for s in signals if s.signal_class == "threat"]
        pressure_signals = [s for s in signals if s.signal_class == "pressure"]
        self.assertEqual(len(threat_signals), 1)
        self.assertEqual(len(pressure_signals), 3)

    def test_summary_distinguishes_threat_and_pressure_counts(self) -> None:
        snapshot = _make_minimal_snapshot()
        pressure_table = ActivePressureTable(
            captured_at=snapshot.captured_at,
            pressures=[
                _make_pressure("safety", "threat_visible"),
                _make_pressure("acquisition", "resource_visible"),
            ],
            updated_at=snapshot.captured_at,
        )
        signals = build_patrol_signals(snapshot, pressure_table)
        summary = summarize_signal_dispatch(signals)
        self.assertEqual(summary.threat_signal_count, 1)
        self.assertEqual(summary.pressure_signal_count, 1)
        self.assertTrue(summary.has_threat_signal)


class LinuxImminentTypesEquivalenceTests(unittest.TestCase):
    """Linux equivalence: declaring all Linux pressure types as imminent
    preserves pre-1.B-4 ``class="threat"`` for every Linux pressure."""

    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_all_linux_pressures_still_emit_threat_class(self) -> None:
        snapshot = ExternalLifeSnapshot(
            captured_at=_utc_now(),
            source_patrol="deep",
            dimensions={
                "runtime_integrity": DimensionSnapshot(status="degraded", evidence={"reason": "x"}),
            },
            overall_status="degraded",
            primary_gap={"type": "runtime_integrity", "reason": "x"},
            trend="worsening",
            updated_at=_utc_now(),
        )
        pressure_table = ActivePressureTable(
            captured_at=snapshot.captured_at,
            pressures=[
                _make_pressure("integrity", "runtime_files_missing"),
                _make_pressure("continuity", "host_continuity_drift"),
                _make_pressure("resource_state", "disk_space_declining"),
                _make_pressure("anomaly_accumulation", "anomaly_count_high"),
            ],
            updated_at=snapshot.captured_at,
        )
        signals = build_patrol_signals(snapshot, pressure_table)
        threat_signals = [s for s in signals if s.signal_class == "threat"]
        pressure_signals = [s for s in signals if s.signal_class == "pressure"]
        self.assertEqual(len(threat_signals), 4)
        self.assertEqual(len(pressure_signals), 0)


if __name__ == "__main__":
    unittest.main()
