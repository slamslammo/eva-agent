"""PR-Α: run_deliberation threads anchor + dlpfc refs into mediator.

After PR-Α changes, ``run_deliberation`` should:
1. Compute an ``anchor_domain_ref`` (deterministic hash of action_set).
2. Extract ``dlpfc_proposal_ref`` from the produced candidates (all candidates
   from one producer call share one ref; first non-None wins).
3. Pass both into ``decide_release`` so the minted ReleaseToken carries them.
"""

from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timezone

from eva.l3_deliberation.contracts import Candidate, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_producer import HeuristicCandidateProducer
from eva.l3_deliberation.runtime import run_deliberation
from scenarios.crafter import activate_crafter_scenario


def _deliberation_input() -> object:
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8, "metabolic": 0.5, "safety": 0.4,
                "recovery": 0.3, "capability": 0.6, "exploration": 0.1,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True, "turn_allowed": True,
            "critical_blocked": False, "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


class _RefAttachingProducer:
    """Test producer: heuristic candidates carrying a fixed dlpfc_proposal_ref."""

    def __init__(self, ref: str) -> None:
        self._ref = ref

    def produce(self, action_domain, deliberation_input):
        base = HeuristicCandidateProducer().produce(action_domain, deliberation_input)
        return [
            dataclasses.replace(
                c,
                parameter_domain={**c.parameter_domain, "dlpfc_proposal_ref": self._ref},
            )
            for c in base
        ]


class RuntimeRefThreadingTests(unittest.TestCase):
    """run_deliberation must thread anchor + dlpfc refs into ReleaseToken."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 28, tzinfo=timezone.utc)

    def test_heuristic_path_token_carries_anchor_domain_ref(self) -> None:
        """Even without an LLM producer, anchor_domain_ref should be computed."""
        di = _deliberation_input()
        audit, _ = run_deliberation(self.now, di)
        token = audit.release_token
        self.assertIsNotNone(token, "Compatibility release should mint a token")
        self.assertIsNotNone(token.anchor_domain_ref)
        self.assertIsInstance(token.anchor_domain_ref, str)
        self.assertTrue(token.anchor_domain_ref.startswith("sha256:") or len(token.anchor_domain_ref) > 0)

    def test_dlpfc_proposal_ref_threaded_from_selected_candidate(self) -> None:
        di = _deliberation_input()
        producer = _RefAttachingProducer(ref="llm_transcripts/dlPFC/turn-000123.json")
        audit, _ = run_deliberation(self.now, di, producer=producer)
        token = audit.release_token
        self.assertIsNotNone(token)
        self.assertEqual(token.dlpfc_proposal_ref, "llm_transcripts/dlPFC/turn-000123.json")

    def test_no_dlpfc_ref_when_candidates_lack_it(self) -> None:
        """Heuristic producer (no LLM) → candidates carry no ref → token ref is None."""
        di = _deliberation_input()
        audit, _ = run_deliberation(self.now, di)  # default HeuristicCandidateProducer
        token = audit.release_token
        self.assertIsNotNone(token)
        # No producer call → no dlpfc_proposal_ref attached.
        self.assertIsNone(token.dlpfc_proposal_ref)

    def test_anchor_domain_ref_deterministic_for_same_action_set(self) -> None:
        """Same anchor admission → same ref hash (deterministic)."""
        di = _deliberation_input()
        a1, _ = run_deliberation(self.now, di)
        a2, _ = run_deliberation(self.now, di)
        self.assertEqual(a1.release_token.anchor_domain_ref, a2.release_token.anchor_domain_ref)


if __name__ == "__main__":
    unittest.main()
