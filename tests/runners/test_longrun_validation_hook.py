"""Round 1.D-3: pin ``runners.longrun_validation`` hook factory behavior.

The hook is the runner-side glue between ``run_runtime``'s periodic
callback and the stability_metrics module. Each fire produces one
numbered profile snapshot on disk and optionally checks tripwire
thresholds.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import argparse

from runners.longrun_validation import (
    LongrunTripwire,
    build_longrun_validation_hook,
    longrun_hook_from_args,
    tripwire_from_args,
)


def _seed_traces(runtime_dir: Path, *, audits: list[dict], outcomes: list[dict], history: list[dict]) -> None:
    """Drop minimal trace files so calculate_stability_profile has input."""

    def _write(path: Path, rows: list[dict]) -> None:
        path.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""), encoding="utf-8")

    runtime_dir.mkdir(parents=True, exist_ok=True)
    _write(runtime_dir / "deliberation_audit.jsonl", audits)
    _write(runtime_dir / "learning_outcomes.jsonl", outcomes)
    _write(runtime_dir / "response_history.jsonl", history)


class LongrunValidationHookTests(unittest.TestCase):
    def test_hook_writes_numbered_snapshot_on_each_fire(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            snapshot_dir = Path(temp_dir) / "snapshots"
            _seed_traces(runtime_dir, audits=[], outcomes=[], history=[])
            hook = build_longrun_validation_hook(snapshot_dir=snapshot_dir)
            self.assertEqual(hook(runtime_dir=runtime_dir, elapsed_since_start=1.0, ticks=10, turns=5), (False, None))
            self.assertEqual(hook(runtime_dir=runtime_dir, elapsed_since_start=2.0, ticks=20, turns=10), (False, None))
            files = sorted(snapshot_dir.glob("profile-*.json"))
            self.assertEqual(len(files), 2)
            self.assertTrue(files[0].name.endswith("00001.json"))
            self.assertTrue(files[1].name.endswith("00002.json"))

    def test_snapshot_includes_elapsed_and_loop_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            snapshot_dir = Path(temp_dir) / "snapshots"
            _seed_traces(runtime_dir, audits=[], outcomes=[], history=[])
            hook = build_longrun_validation_hook(snapshot_dir=snapshot_dir)
            hook(runtime_dir=runtime_dir, elapsed_since_start=123.456, ticks=42, turns=7)
            payload = json.loads((snapshot_dir / "profile-00001.json").read_text())
            self.assertEqual(payload["sequence"], 1)
            self.assertEqual(payload["elapsed_since_start_sec"], 123.456)
            self.assertEqual(payload["ticks"], 42)
            self.assertEqual(payload["turns"], 7)
            # The annotated payload preserves the standard stability_profile
            # surface (metrics + metadata) so consumers can analyse it the
            # same way as a regular profile file.
            self.assertIn("metrics", payload)

    def test_no_tripwire_returns_false_when_threshold_not_violated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            snapshot_dir = Path(temp_dir) / "snapshots"
            # Audits with zero violations satisfy max_constraint_violation_rate=0.0
            _seed_traces(
                runtime_dir,
                audits=[
                    {
                        "release_decision": {"outcome": "withhold"},
                        "deliberation_input": {
                            "runtime_gate_context": {
                                "instance_valid": True,
                                "turn_allowed": True,
                                "critical_blocked": False,
                                "life_state": "STABLE",
                            }
                        },
                    }
                ],
                outcomes=[],
                history=[],
            )
            hook = build_longrun_validation_hook(
                snapshot_dir=snapshot_dir,
                tripwire=LongrunTripwire(),
            )
            result = hook(runtime_dir=runtime_dir, elapsed_since_start=1.0, ticks=1, turns=0)
            self.assertEqual(result, (False, None))

    def test_tripwire_fires_on_constraint_violation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            snapshot_dir = Path(temp_dir) / "snapshots"
            # Audit with non-withhold outcome under a critical_blocked runtime
            # gate counts as a constraint violation in the metrics module.
            _seed_traces(
                runtime_dir,
                audits=[
                    {
                        "release_decision": {"outcome": "release"},
                        "deliberation_input": {"runtime_gate_context": {"instance_valid": True, "turn_allowed": True, "critical_blocked": True}},
                    }
                ],
                outcomes=[],
                history=[],
            )
            hook = build_longrun_validation_hook(
                snapshot_dir=snapshot_dir,
                tripwire=LongrunTripwire(max_constraint_violation_rate=0.0),
            )
            should_stop, reason = hook(runtime_dir=runtime_dir, elapsed_since_start=1.0, ticks=1, turns=0)
            self.assertTrue(should_stop)
            self.assertIsNotNone(reason)
            self.assertIn("constraint_violation_rate", reason or "")

    def test_no_tripwire_arg_is_snapshot_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir) / "runtime"
            snapshot_dir = Path(temp_dir) / "snapshots"
            _seed_traces(runtime_dir, audits=[], outcomes=[], history=[])
            hook = build_longrun_validation_hook(snapshot_dir=snapshot_dir, tripwire=None)
            result = hook(runtime_dir=runtime_dir, elapsed_since_start=1.0, ticks=1, turns=0)
            self.assertEqual(result, (False, None))
            self.assertTrue((snapshot_dir / "profile-00001.json").exists())


class CLIArgsTranslationTests(unittest.TestCase):
    """Cover the parse_args() → hook translation helpers."""

    def _ns(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "longrun_snapshot_dir": None,
            "longrun_hook_interval_sec": 1800.0,
            "longrun_tripwire_max_constraint_violation_rate": 0.0,
            "longrun_tripwire_min_continuity_score": 0.5,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_tripwire_from_args_default_thresholds(self) -> None:
        tripwire = tripwire_from_args(self._ns())
        self.assertEqual(tripwire.max_constraint_violation_rate, 0.0)
        self.assertEqual(tripwire.min_continuity_preservation_score, 0.5)
        self.assertIsNone(tripwire.min_useful_progress_under_constraint)

    def test_tripwire_from_args_negative_disables(self) -> None:
        tripwire = tripwire_from_args(self._ns(
            longrun_tripwire_max_constraint_violation_rate=-1.0,
            longrun_tripwire_min_continuity_score=-1.0,
        ))
        self.assertIsNone(tripwire.max_constraint_violation_rate)
        self.assertIsNone(tripwire.min_continuity_preservation_score)

    def test_hook_from_args_returns_none_when_snapshot_dir_unset(self) -> None:
        self.assertIsNone(longrun_hook_from_args(self._ns()))

    def test_hook_from_args_returns_callable_when_snapshot_dir_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hook = longrun_hook_from_args(self._ns(longrun_snapshot_dir=temp_dir))
            self.assertIsNotNone(hook)
            self.assertTrue(callable(hook))


if __name__ == "__main__":
    unittest.main()
