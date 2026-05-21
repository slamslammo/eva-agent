"""Round 1.G — CandidateProducer seam tests (dlPFC candidate production).

Pins the phase-1 invariants: the deterministic HeuristicCandidateProducer reproduces
the pre-1.G candidate set (behavior-preserving), satisfies the CandidateProducer
protocol, exposes no selection/release surface (LLM never releases), and is the
behavior-preserving default in run_deliberation.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from eva.anchor import build_action_domain
from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.reasoning import build_candidates
from eva.l3_deliberation.reasoning.candidate_producer import (
    CandidateProducer,
    HeuristicCandidateProducer,
)
from eva.l3_deliberation.runtime import run_deliberation
from scenarios.crafter import activate_crafter_scenario


def _deliberation_input():
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8,
                "metabolic": 0.5,
                "safety": 0.4,
                "recovery": 0.3,
                "capability": 0.6,
                "exploration": 0.1,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


class CandidateProducerTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)

    def test_heuristic_producer_equals_build_candidates(self) -> None:
        di = _deliberation_input()
        domain = build_action_domain(di)
        produced = HeuristicCandidateProducer().produce(domain, di)
        baseline = build_candidates(domain)
        self.assertEqual([c.candidate_id for c in produced], [c.candidate_id for c in baseline])
        self.assertEqual([c.action for c in produced], [c.action for c in baseline])

    def test_heuristic_satisfies_candidate_producer_protocol(self) -> None:
        self.assertIsInstance(HeuristicCandidateProducer(), CandidateProducer)

    def test_producer_has_no_release_or_select_surface(self) -> None:
        producer = HeuristicCandidateProducer()
        self.assertFalse(hasattr(producer, "release"))
        self.assertFalse(hasattr(producer, "select"))

    def test_run_deliberation_default_producer_is_behavior_preserving(self) -> None:
        di = _deliberation_input()
        domain = build_action_domain(di)
        expected = [c.candidate_id for c in build_candidates(domain)]
        audit_default, _ = run_deliberation(self.now, di)
        audit_explicit, _ = run_deliberation(self.now, di, producer=HeuristicCandidateProducer())
        self.assertEqual([c["candidate_id"] for c in audit_default.candidates], expected)
        self.assertEqual(
            [c["candidate_id"] for c in audit_default.candidates],
            [c["candidate_id"] for c in audit_explicit.candidates],
        )


if __name__ == "__main__":
    unittest.main()
