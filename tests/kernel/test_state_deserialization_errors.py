"""Round 1.B-1-e: pin that ``ActivePressure.from_dict`` and
``DriveState.from_dict`` fail loudly on malformed payloads instead of
silently defaulting to Linux drive vocabulary.

Pre-fix:
- ``ActivePressure.from_dict({...})`` with no ``type`` key returned a pressure
  with ``type="continuity"`` (a Linux drive name).
- ``DriveState.from_dict({...})`` with no ``drive_type`` key returned a drive
  with ``drive_type="survival"`` (another Linux drive name).

These defaults were dead in practice — production serializers always set
both fields. They were Linux-vocabulary residue that would mask schema bugs
if ever reached. Post-fix the deserializers raise a clear error for missing
required fields.
"""

from __future__ import annotations

import unittest

from eva.kernel import utc_now
from eva.kernel.state import ActivePressure, DriveState


class ActivePressureDeserializationTests(unittest.TestCase):
    def test_active_pressure_requires_type(self) -> None:
        """Round 1.B-1-e: missing ``type`` raises rather than silently
        defaulting to the Linux drive name "continuity"."""

        with self.assertRaises(KeyError) as ctx:
            ActivePressure.from_dict({"pressure_id": "p-1"})
        self.assertIn("type", str(ctx.exception))

    def test_active_pressure_well_formed_payload_round_trips(self) -> None:
        """Sanity: well-formed payload still deserializes cleanly."""

        now = utc_now()
        payload = {
            "pressure_id": "p-1",
            "type": "acquisition",  # any scenario's pressure type works
            "severity": "degraded",
            "evidence": {"reason": "test"},
            "first_seen_at": now.isoformat().replace("+00:00", "Z"),
            "last_seen_at": now.isoformat().replace("+00:00", "Z"),
        }
        pressure = ActivePressure.from_dict(payload)
        self.assertEqual(pressure.pressure_id, "p-1")
        self.assertEqual(pressure.type, "acquisition")


class DriveStateDeserializationTests(unittest.TestCase):
    def test_drive_state_requires_drive_type(self) -> None:
        """Round 1.B-1-e: missing ``drive_type`` raises rather than silently
        defaulting to the Linux drive name "survival"."""

        with self.assertRaises(KeyError) as ctx:
            DriveState.from_dict({})
        self.assertIn("drive_type", str(ctx.exception))

    def test_drive_state_well_formed_payload_round_trips(self) -> None:
        """Sanity: well-formed payload still deserializes cleanly."""

        payload = {
            "drive_type": "metabolic",
            "level": 0.4,
            "delta": 0.0,
            "trend": "stable",
            "contributors": [],
        }
        drive_state = DriveState.from_dict(payload)
        self.assertEqual(drive_state.drive_type, "metabolic")
        self.assertEqual(drive_state.level, 0.4)


if __name__ == "__main__":
    unittest.main()
