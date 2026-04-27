from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from eva.kernel import ActiveInstanceRecord, InstanceGuard, LifecycleConfig, StateStore, build_runtime_paths, utc_now


class InstanceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StateStore(build_runtime_paths(self.temp_dir.name))
        self.lifecycle = LifecycleConfig(heartbeat_interval_sec=1.0, lease_duration_sec=2.0)
        self.guard = InstanceGuard(self.store.paths.lock_file, self.store, self.lifecycle)
        self.guard.acquire()
        self.guard.start_instance("eva-test-instance")

    def tearDown(self) -> None:
        self.guard.release()
        self.temp_dir.cleanup()

    def test_snapshot_is_valid_after_start(self) -> None:
        snapshot = self.guard.snapshot()
        self.assertTrue(snapshot.lock_held)
        self.assertTrue(snapshot.generation_matches)
        self.assertTrue(snapshot.lease_not_expired)
        self.assertTrue(snapshot.instance_valid)

    def test_generation_mismatch_invalidates_instance(self) -> None:
        current = self.store.read_active_instance()
        assert current is not None
        self.store.write_active_instance(
            ActiveInstanceRecord(
                instance_id=current.instance_id,
                generation=current.generation + 1,
                lease_expires_at=current.lease_expires_at,
                lock_holder=True,
                updated_at=utc_now(),
            )
        )
        snapshot = self.guard.snapshot()
        self.assertFalse(snapshot.generation_matches)
        self.assertFalse(snapshot.instance_valid)

    def test_expired_lease_invalidates_instance(self) -> None:
        current = self.store.read_active_instance()
        assert current is not None
        self.store.write_active_instance(
            ActiveInstanceRecord(
                instance_id=current.instance_id,
                generation=current.generation,
                lease_expires_at=utc_now() - timedelta(seconds=1),
                lock_holder=True,
                updated_at=utc_now(),
            )
        )
        snapshot = self.guard.snapshot()
        self.assertFalse(snapshot.lease_not_expired)
        self.assertFalse(snapshot.instance_valid)

    def test_second_process_cannot_acquire_same_lock(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo_root)
        script = """
from eva.kernel import InstanceGuard, LifecycleConfig, StateStore, build_runtime_paths
import sys

store = StateStore(build_runtime_paths(sys.argv[1]))
guard = InstanceGuard(store.paths.lock_file, store, LifecycleConfig())
try:
    guard.acquire()
except BlockingIOError:
    print('blocked')
    raise SystemExit(0)
else:
    print('acquired')
    raise SystemExit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, self.temp_dir.name],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertIn("blocked", result.stdout)


if __name__ == "__main__":
    unittest.main()
