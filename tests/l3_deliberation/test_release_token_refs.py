"""PR-Α: ReleaseToken auditable-ref fields.

Adds three optional reference fields (default ``None``) so each release token
can carry back-pointers to the anchor domain, the dlPFC LLM transcript, and
the OFC assessment. PR-Α covers anchor + dlPFC refs; OFC ref placeholder is
filled by PR-Γ.

Red lines:
- R4: Old construction sites pass nothing → field defaults must keep them
  byte-compatible (Linux scenario regression).
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import ReleaseToken


class ReleaseTokenBackwardCompatibilityTests(unittest.TestCase):
    """R4: Existing positional/keyword construction must keep working."""

    def test_construction_with_only_legacy_fields_keeps_refs_none(self) -> None:
        token = ReleaseToken(
            token_id="t1",
            outcome="compatibility_release",
            candidate_id="c1",
            candidate_profile="crafter_raw_action",
        )
        self.assertIsNone(token.anchor_domain_ref)
        self.assertIsNone(token.dlpfc_proposal_ref)
        self.assertIsNone(token.ofc_assessment_ref)

    def test_equality_unaffected_by_default_refs(self) -> None:
        a = ReleaseToken(token_id="t", outcome="o", candidate_id="c", candidate_profile="p")
        b = ReleaseToken(token_id="t", outcome="o", candidate_id="c", candidate_profile="p")
        self.assertEqual(a, b)


class ReleaseTokenWithRefsTests(unittest.TestCase):
    """PR-Α: each ref may be provided as optional kwarg."""

    def test_anchor_domain_ref_set(self) -> None:
        token = ReleaseToken(
            token_id="t1", outcome="o", candidate_id="c", candidate_profile="p",
            anchor_domain_ref="sha256:abcd1234",
        )
        self.assertEqual(token.anchor_domain_ref, "sha256:abcd1234")
        self.assertIsNone(token.dlpfc_proposal_ref)
        self.assertIsNone(token.ofc_assessment_ref)

    def test_dlpfc_proposal_ref_set(self) -> None:
        token = ReleaseToken(
            token_id="t1", outcome="o", candidate_id="c", candidate_profile="p",
            dlpfc_proposal_ref="llm_transcripts/dlPFC/turn-000007.json",
        )
        self.assertEqual(token.dlpfc_proposal_ref, "llm_transcripts/dlPFC/turn-000007.json")

    def test_all_three_refs_can_be_set_independently(self) -> None:
        token = ReleaseToken(
            token_id="t1", outcome="o", candidate_id="c", candidate_profile="p",
            anchor_domain_ref="hash:a",
            dlpfc_proposal_ref="path:b",
            ofc_assessment_ref="path:c",
        )
        self.assertEqual(token.anchor_domain_ref, "hash:a")
        self.assertEqual(token.dlpfc_proposal_ref, "path:b")
        self.assertEqual(token.ofc_assessment_ref, "path:c")

    def test_token_remains_frozen_dataclass(self) -> None:
        token = ReleaseToken(token_id="t", outcome="o", candidate_id="c", candidate_profile="p")
        with self.assertRaises(Exception):
            token.anchor_domain_ref = "x"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
