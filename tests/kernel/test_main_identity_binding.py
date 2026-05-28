"""PR-Α: ``run_runtime`` binds identity_provider onto the candidate producer.

When the candidate producer exposes a ``set_identity_provider`` method,
``run_runtime`` should bind it with a closure that returns the current
``run_id`` / ``individual_id`` / ``turn_index`` at call time so the
transcript sink can stamp each LLM call with correct identity.

Producers without ``set_identity_provider`` are untouched (Linux compat).
"""

from __future__ import annotations

import tempfile
import unittest

from eva.kernel import (
    ExternalLifeConfig,
    LifecycleConfig,
    LoopControl,
    build_runtime_config,
)
from eva.kernel.main import run_runtime
from scenarios.crafter import activate_crafter_scenario


class _IdentityCapturingProducer:
    """Stub producer that records the identity callable bound to it."""

    def __init__(self) -> None:
        self.captured_provider = None
        self.captured_identity_snapshot = None

    def produce(self, action_domain, deliberation_input):
        # If identity provider was bound, snapshot what it returns at produce time.
        if self.captured_provider is not None:
            self.captured_identity_snapshot = self.captured_provider()
        return []

    def set_identity_provider(self, provider) -> None:
        self.captured_provider = provider


class IdentityBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_run_runtime_binds_identity_provider_with_run_individual_turn(self) -> None:
        producer = _IdentityCapturingProducer()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=4, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            run_runtime(config, candidate_producer=producer)

        # set_identity_provider must have been called.
        self.assertIsNotNone(producer.captured_provider,
                             "run_runtime must call set_identity_provider on producers that expose it")
        snapshot = producer.captured_identity_snapshot
        self.assertIsNotNone(snapshot)
        self.assertIn("run_id", snapshot)
        self.assertIn("individual_id", snapshot)
        self.assertIn("turn_index", snapshot)
        self.assertTrue(snapshot["run_id"], "run_id must be a non-empty string")
        self.assertTrue(snapshot["individual_id"], "individual_id must be a non-empty string")
        self.assertIsInstance(snapshot["turn_index"], int)

    def test_producer_without_set_identity_provider_is_untouched(self) -> None:
        """Linux compat: producers that don't expose the method are not modified."""

        class _MinimalProducer:
            def produce(self, action_domain, deliberation_input):
                return []

        producer = _MinimalProducer()

        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                lifecycle=LifecycleConfig(
                    heartbeat_interval_sec=0.2,
                    lease_duration_sec=1.0,
                    recovering_window_sec=0.05,
                    turn_guard_window_sec=0.01,
                ),
                external_life=ExternalLifeConfig(
                    shallow_patrol_interval_sec=0.01,
                    deep_patrol_interval_sec=0.02,
                    full_report_interval_sec=0.03,
                    recent_event_window_sec=60.0,
                ),
                control=LoopControl(max_turns=2, max_runtime_sec=1.0, idle_sleep_sec=0.01),
            )
            # Should not raise.
            run_runtime(config, candidate_producer=producer)


if __name__ == "__main__":
    unittest.main()
