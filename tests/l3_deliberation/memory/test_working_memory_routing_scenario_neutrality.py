"""Round 1.B-1-d: pin that working_memory adapter / model client routing is
scenario-neutral.

Pre-fix: both `working_memory_adapter.py` and `working_memory_model_client.py`
gated the "prefer stabilize_first" branch on ``top_drive == "integrity"``. For
Crafter (whose top_drive is never literally "integrity"), this branch was
dead code; Crafter always took the fallback "prefer observe_first" branch
regardless of how much pressure the avatar was under.

Post-fix: the same routing decision is made on the basis of
``top_drive_level >= HIGH_DRIVE_PROJECTION_THRESHOLD``. This is bit-equivalent
for Linux (when ``top_drive == "integrity"``, its level is essentially always
≥ 0.5 in any state that previously triggered the branch) and finally engages
the stabilize-routing path for Crafter under high drive pressure.
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.memory.working_memory_adapter import (
    HeuristicWorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
)
from eva.l3_deliberation.memory.working_memory_model_client import (
    HeuristicWorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
)


def _make_adapter_request(*, top_drive: str, drive_levels: dict[str, float]) -> WorkingMemoryAdapterRequest:
    return WorkingMemoryAdapterRequest(
        situation_key=f"{top_drive}|STABLE|test",
        drive_broadcast={
            "top_drive": top_drive,
            "drive_levels": dict(drive_levels),
            "drive_trends": {drive: "stable" for drive in drive_levels},
        },
        runtime_gate_context={
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
            "seconds_to_heartbeat": 10.0,
        },
        bias_summaries=[],
        habit_skills=[],
        recent_relevant_outcomes=[],
        semantic_patterns=[],
        inherited_priors=[],
        local_confidence=0.5,
    )


def _make_client_payload(*, top_drive: str, drive_levels: dict[str, float], conservative_mode: bool = False) -> dict[str, object]:
    return {
        "situation_key": f"{top_drive}|STABLE|test",
        "drive_broadcast": {
            "top_drive": top_drive,
            "drive_levels": dict(drive_levels),
            "drive_trends": {drive: "stable" for drive in drive_levels},
        },
        "runtime_gate_context": {
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": conservative_mode,
            "life_state": "STABLE",
            "seconds_to_heartbeat": 10.0,
        },
        "local_confidence": 0.5,
    }


class WorkingMemoryAdapterRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = HeuristicWorkingMemoryAdapter()

    def test_crafter_high_drive_routes_to_stabilize(self) -> None:
        """Pre-fix: Crafter top_drive='safety' never matched 'integrity', so
        the adapter always took the observe_first branch. Post-fix: a high
        safety drive routes to stabilize_first."""

        request = _make_adapter_request(
            top_drive="safety",
            drive_levels={"safety": 0.85, "metabolic": 0.2, "acquisition": 0.1},
        )
        response = self.adapter.build_advisory_context(request)
        self.assertEqual(
            list(response.candidate_suggestions),
            ["stabilize_first"],
            f"Crafter high safety should route to stabilize_first; "
            f"got {response.candidate_suggestions} with reasoning {response.reasoning_trace}",
        )

    def test_linux_high_integrity_still_routes_to_stabilize(self) -> None:
        """Linux equivalence: high integrity drive must still route to
        stabilize_first."""

        request = _make_adapter_request(
            top_drive="integrity",
            drive_levels={"integrity": 0.85, "curiosity": 0.2},
        )
        response = self.adapter.build_advisory_context(request)
        self.assertEqual(list(response.candidate_suggestions), ["stabilize_first"])

    def test_low_drive_routes_to_observe(self) -> None:
        """When the top drive is below the high threshold, routing falls back
        to observe_first regardless of scenario."""

        request = _make_adapter_request(
            top_drive="acquisition",
            drive_levels={"acquisition": 0.3, "safety": 0.1},
        )
        response = self.adapter.build_advisory_context(request)
        self.assertEqual(list(response.candidate_suggestions), ["observe_first"])


class WorkingMemoryModelClientRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = HeuristicWorkingMemoryModelClient(
            WorkingMemoryModelClientConfig(provider="heuristic", model="rule_based")
        )

    def test_crafter_high_drive_routes_to_stabilize(self) -> None:
        request = WorkingMemoryModelClientRequest(
            payload=_make_client_payload(
                top_drive="metabolic",
                drive_levels={"metabolic": 0.8, "safety": 0.2},
            )
        )
        response = self.client.build_working_memory_advisory(request)
        self.assertEqual(
            list(response.payload.get("candidate_suggestions", [])),
            ["stabilize_first"],
        )

    def test_linux_high_integrity_still_routes_to_stabilize(self) -> None:
        request = WorkingMemoryModelClientRequest(
            payload=_make_client_payload(
                top_drive="integrity",
                drive_levels={"integrity": 0.85, "curiosity": 0.2},
            )
        )
        response = self.client.build_working_memory_advisory(request)
        self.assertEqual(
            list(response.payload.get("candidate_suggestions", [])),
            ["stabilize_first"],
        )

    def test_conservative_mode_routes_to_stabilize_regardless_of_drive_level(self) -> None:
        """Conservative mode is independent of drive level — preserves
        the OR-with-conservative-mode semantic from the original code."""

        request = WorkingMemoryModelClientRequest(
            payload=_make_client_payload(
                top_drive="acquisition",
                drive_levels={"acquisition": 0.2},
                conservative_mode=True,
            )
        )
        response = self.client.build_working_memory_advisory(request)
        self.assertEqual(
            list(response.payload.get("candidate_suggestions", [])),
            ["stabilize_first"],
        )

    def test_low_drive_routes_to_observe(self) -> None:
        request = WorkingMemoryModelClientRequest(
            payload=_make_client_payload(
                top_drive="capability",
                drive_levels={"capability": 0.25},
            )
        )
        response = self.client.build_working_memory_advisory(request)
        self.assertEqual(
            list(response.payload.get("candidate_suggestions", [])),
            ["observe_first"],
        )


if __name__ == "__main__":
    unittest.main()
