"""crafter-world-map-observer-trace slice 3 — runner session wires the sink.

CrafterRuntimeSession.start() builds an observer-only JsonlWorldTraceSink and
hands it to the wrapper ONLY when EVA_TRACE is on AND a runtime_dir is given —
mirroring how raw_observations is gated. Off / no-dir → no sink (byte-for-byte
unchanged run). This is the seam that lets a live run emit world_trace.jsonl.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock


class SessionWorldTraceWiringTests(unittest.TestCase):
    def test_no_sink_when_trace_off(self) -> None:
        from runners.run_crafter import _build_world_trace_sink

        with mock.patch.dict(os.environ, {"EVA_TRACE": ""}, clear=False):
            self.assertIsNone(_build_world_trace_sink("/tmp/whatever"))

    def test_no_sink_when_runtime_dir_none(self) -> None:
        from runners.run_crafter import _build_world_trace_sink

        with mock.patch.dict(os.environ, {"EVA_TRACE": "1"}, clear=False):
            self.assertIsNone(_build_world_trace_sink(None))

    def test_sink_built_when_trace_on_and_dir_given(self) -> None:
        from runners.run_crafter import _build_world_trace_sink
        from scenarios.crafter.wrapper.world_trace import JsonlWorldTraceSink

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"EVA_TRACE": "1"}, clear=False):
                sink = _build_world_trace_sink(temp_dir)
            self.assertIsInstance(sink, JsonlWorldTraceSink)

    def test_start_accepts_runtime_dir_and_passes_sink_to_wrapper(self) -> None:
        # start(seed, runtime_dir=...) must build + inject the sink under EVA_TRACE.
        # Patch CrafterEnvWrapper to capture the world_trace_sink it receives,
        # avoiding a real Crafter install.
        import runners.run_crafter as rc

        captured = {}

        class _FakeWrapper:
            def __init__(self, *, seed=None, world_trace_sink=None):
                captured["sink"] = world_trace_sink

            def reset(self, *, seed=None):
                return {"visible": {}}

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(rc, "CrafterEnvWrapper", _FakeWrapper):
                with mock.patch.dict(os.environ, {"EVA_TRACE": "1"}, clear=False):
                    rc.CrafterRuntimeSession.start(seed=42, runtime_dir=temp_dir)
        from scenarios.crafter.wrapper.world_trace import JsonlWorldTraceSink

        self.assertIsInstance(captured["sink"], JsonlWorldTraceSink)

    def test_start_default_runtime_dir_none_no_sink(self) -> None:
        # Back-compat: start(seed=...) with no runtime_dir builds no sink.
        import runners.run_crafter as rc

        captured = {}

        class _FakeWrapper:
            def __init__(self, *, seed=None, world_trace_sink=None):
                captured["sink"] = world_trace_sink

            def reset(self, *, seed=None):
                return {"visible": {}}

        with mock.patch.object(rc, "CrafterEnvWrapper", _FakeWrapper):
            with mock.patch.dict(os.environ, {"EVA_TRACE": "1"}, clear=False):
                rc.CrafterRuntimeSession.start(seed=42)
        self.assertIsNone(captured["sink"])


if __name__ == "__main__":
    unittest.main()
