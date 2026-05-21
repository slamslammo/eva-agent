"""Round 1.H H-1 — TraceSink foundation tests (envelope, run_meta, opt-in flag).

Pins: opt-in flag default off; NullTraceSink no-ops and writes nothing (byte-equivalent);
JsonlTraceSink writes schema-conformant envelopes + run_meta; continuity_state updates.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eva.observability import (
    CONTINUITY_TERMINATED,
    NullTraceSink,
    RunIdentity,
    build_trace_sink,
    trace_enabled,
    write_run_meta,
)

_ENVELOPE_KEYS = {
    "run_id",
    "individual_id",
    "individual_boundary",
    "continuity_state",
    "inherited_from",
    "episode_step",
    "turn_index",
    "event_type",
    "ts",
}


def _identity() -> RunIdentity:
    return RunIdentity(
        run_id="run-1",
        individual_id="ind-1",
        individual_boundary="one_crafter_life",
        continuity_state="alive",
    )


class TraceFlagTests(unittest.TestCase):
    def test_flag_off_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EVA_TRACE", None)
            self.assertFalse(trace_enabled())

    def test_flag_truthy_values(self) -> None:
        for val, expected in [("1", True), ("true", True), ("0", False), ("", False), ("off", False)]:
            with patch.dict(os.environ, {"EVA_TRACE": val}):
                self.assertEqual(trace_enabled(), expected, val)


class NullSinkTests(unittest.TestCase):
    def test_disabled_returns_null_sink_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=False, identity=_identity())
            self.assertIsInstance(sink, NullTraceSink)
            self.assertFalse(sink.enabled)
            sink.emit_transform(layer="L1", transform_id="x", code_anchor="m:f", turn_index=0)
            sink.emit_snapshot(snapshot_type="drive_state", values={}, turn_index=0)
            sink.set_continuity_state(CONTINUITY_TERMINATED)
            self.assertEqual(list(Path(tmp).iterdir()), [])  # no files written

    def test_missing_identity_returns_null_sink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsInstance(build_trace_sink(tmp, enabled=True, identity=None), NullTraceSink)


class JsonlSinkTests(unittest.TestCase):
    def _read_trace(self, tmp: str) -> list[dict]:
        lines = (Path(tmp) / "cognitive_trace.jsonl").read_text().strip().splitlines()
        return [json.loads(line) for line in lines]

    def test_emit_transform_writes_conformant_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=True, identity=_identity())
            self.assertTrue(sink.enabled)
            sink.emit_transform(
                layer="L3",
                transform_id="l3.candidate_produce",
                code_anchor="eva/.../llm_candidate_producer.py:produce",
                turn_index=5,
                inputs={"gate": "ok"},
                outputs={"candidates": 3},
                decision="produced",
                parents=[{"id": "anchor.admit", "edge_type": "pressure"}],
            )
            records = self._read_trace(tmp)
            self.assertEqual(len(records), 1)
            rec = records[0]
            self.assertTrue(_ENVELOPE_KEYS.issubset(rec.keys()))
            self.assertEqual(rec["event_type"], "transform")
            self.assertEqual(rec["turn_index"], 5)
            self.assertEqual(rec["transform_id"], "l3.candidate_produce")
            self.assertEqual(rec["layer"], "L3")
            self.assertEqual(rec["parents"], [{"id": "anchor.admit", "edge_type": "pressure"}])

    def test_emit_snapshot_writes_snapshot_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=True, identity=_identity())
            sink.emit_snapshot(
                snapshot_type="drive_state",
                values={"metabolic": 0.4, "safety": 0.2},
                turn_index=2,
            )
            rec = self._read_trace(tmp)[0]
            self.assertEqual(rec["event_type"], "snapshot")
            self.assertEqual(rec["snapshot_type"], "drive_state")
            self.assertEqual(rec["values"]["metabolic"], 0.4)

    def test_continuity_state_update_reflected_in_later_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = build_trace_sink(tmp, enabled=True, identity=_identity())
            sink.emit_snapshot(snapshot_type="drive_state", values={}, turn_index=0)
            sink.set_continuity_state(CONTINUITY_TERMINATED)
            sink.emit_snapshot(snapshot_type="drive_state", values={}, turn_index=1)
            records = self._read_trace(tmp)
            self.assertEqual(records[0]["continuity_state"], "alive")
            self.assertEqual(records[1]["continuity_state"], CONTINUITY_TERMINATED)

    def test_write_run_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_run_meta(tmp, {"run_id": "run-1", "scenario": "crafter", "seed": 1})
            meta = json.loads((Path(tmp) / "run_meta.json").read_text())
            self.assertEqual(meta["run_id"], "run-1")
            self.assertEqual(meta["scenario"], "crafter")
            self.assertEqual(meta["seed"], 1)


if __name__ == "__main__":
    unittest.main()
