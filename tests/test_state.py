from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.config import build_runtime_paths
from eva.state import ActiveInstanceRecord, EventRecord, RuntimeState, StateStore, utc_now


class StateStoreTests(unittest.TestCase):
    def test_write_and_read_active_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            record = ActiveInstanceRecord(
                instance_id="eva-test-001",
                generation=1,
                lease_expires_at=now + timedelta(seconds=5),
                lock_holder=True,
                updated_at=now,
            )
            store.write_active_instance(record)
            loaded = store.read_active_instance()
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.instance_id, record.instance_id)
            self.assertEqual(loaded.generation, record.generation)
            self.assertTrue(loaded.lock_holder)

    def test_write_and_read_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = RuntimeState(
                life_state="STABLE",
                last_tick_id="tick-0001",
                last_turn_id="turn-0001",
                heartbeat_ok=True,
                tick_ok=True,
                state_io_ok=True,
                instance_valid=True,
                updated_at=now,
            )
            store.write_runtime_state(state)
            loaded = store.read_runtime_state()
            self.assertEqual(loaded.life_state, "STABLE")
            self.assertEqual(loaded.last_tick_id, "tick-0001")
            self.assertTrue(loaded.instance_valid)

    def test_append_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            store.append_event(EventRecord(event_type="startup", timestamp=now, details={"step": 1}))
            store.append_event(EventRecord(event_type="shutdown", timestamp=now, details={"step": 2}))
            events = store.read_events()
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["event_type"], "startup")
            self.assertEqual(events[1]["event_type"], "shutdown")

    def test_runtime_state_overwrite_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            first = RuntimeState(life_state="RECOVERING")
            second = RuntimeState(life_state="STABLE", heartbeat_ok=True, instance_valid=True)
            store.write_runtime_state(first)
            store.write_runtime_state(second)
            loaded = store.read_runtime_state()
            self.assertEqual(loaded.life_state, "STABLE")
            self.assertTrue(loaded.heartbeat_ok)


if __name__ == "__main__":
    unittest.main()
