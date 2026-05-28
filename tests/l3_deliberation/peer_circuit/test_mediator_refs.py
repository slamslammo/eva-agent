"""PR-Α: ``decide_release`` accepts and propagates auditable refs.

When ``decide_release`` constructs a ``ReleaseToken`` (on
``compatibility_release`` outcome), it should embed the optional
``anchor_domain_ref`` and ``dlpfc_proposal_ref`` kwargs passed in by the
caller. ``ofc_assessment_ref`` stays None (PR-Γ fills it).

Red lines:
- R4: Calling ``decide_release`` without the new kwargs must produce the same
  token as before (Linux compatibility).
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import CandidateAssessment
from eva.l3_deliberation.peer_circuit.mediator import decide_release
from scenarios.linux_runtime import activate_linux_runtime_scenario


def _assessment(action: str = "noop", *, candidate_id: str = "candidate-x") -> CandidateAssessment:
    return CandidateAssessment(
        candidate_id=candidate_id,
        action=action,
        score=1.0,
        disposition="allow",
        reasons=("ok",),
    )


class DecideReleaseRefPropagationTests(unittest.TestCase):
    """``decide_release`` embeds refs into the resulting ReleaseToken."""

    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_decide_release_without_refs_keeps_token_refs_none(self) -> None:
        decision = decide_release([_assessment()])
        self.assertEqual(decision.outcome, "compatibility_release")
        self.assertIsNotNone(decision.release_token)
        self.assertIsNone(decision.release_token.anchor_domain_ref)
        self.assertIsNone(decision.release_token.dlpfc_proposal_ref)
        self.assertIsNone(decision.release_token.ofc_assessment_ref)

    def test_decide_release_with_anchor_domain_ref_propagates_into_token(self) -> None:
        decision = decide_release(
            [_assessment()],
            anchor_domain_ref="sha256:deadbeef",
        )
        self.assertEqual(decision.release_token.anchor_domain_ref, "sha256:deadbeef")
        # dlpfc / ofc remain placeholders
        self.assertIsNone(decision.release_token.dlpfc_proposal_ref)
        self.assertIsNone(decision.release_token.ofc_assessment_ref)

    def test_decide_release_with_dlpfc_proposal_ref_propagates_into_token(self) -> None:
        decision = decide_release(
            [_assessment()],
            dlpfc_proposal_ref="llm_transcripts/dlPFC/turn-000005.json",
        )
        self.assertEqual(
            decision.release_token.dlpfc_proposal_ref,
            "llm_transcripts/dlPFC/turn-000005.json",
        )
        self.assertIsNone(decision.release_token.anchor_domain_ref)
        self.assertIsNone(decision.release_token.ofc_assessment_ref)

    def test_decide_release_with_both_refs_propagates_both(self) -> None:
        decision = decide_release(
            [_assessment()],
            anchor_domain_ref="hash:abc",
            dlpfc_proposal_ref="path:xyz",
        )
        self.assertEqual(decision.release_token.anchor_domain_ref, "hash:abc")
        self.assertEqual(decision.release_token.dlpfc_proposal_ref, "path:xyz")
        self.assertIsNone(decision.release_token.ofc_assessment_ref)

    def test_decide_release_defer_outcome_unchanged_by_refs(self) -> None:
        """Refs are only embedded when a token is minted (compatibility_release).

        Defer / withhold paths don't produce a token, so passing refs is a no-op.
        """
        deferred = CandidateAssessment(
            candidate_id="def-c", action="noop", disposition="defer",
            score=0.0, reasons=(),
        )
        decision = decide_release(
            [deferred],
            anchor_domain_ref="should-be-ignored",
            dlpfc_proposal_ref="should-be-ignored",
        )
        # Defer path returns no release_token (existing behavior).
        self.assertIsNone(decision.release_token)


if __name__ == "__main__":
    unittest.main()
