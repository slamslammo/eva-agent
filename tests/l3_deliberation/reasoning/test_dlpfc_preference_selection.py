"""PR-O2 slice 2: end-to-end proof that dlpfc_preference fixes the move_right bug.

The 62%-flat-tie病 (T3): when the LLM proposes several candidates that share
the same drive/projection/experience inputs, OFC scored them all identically.
``select_allowed_assessment`` then fell through to its final ``candidate_id``
lexical tiebreak (``max`` → the alphabetically *largest* id), so the dlPFC's
preference order was silently discarded — the agent acted on whichever action
name happened to sort last, not on what the dlPFC actually preferred.

PR-O2 adds a dlpfc_preference rank term to the OFC score for dlPFC-produced
(LLM) candidates, so identical-input candidates now score rank0 > rank1 > rank2.
The flat tie is gone, ``max`` picks rank0, and the ``candidate_id`` tiebreak is
never reached for LLM candidates — *without touching selection.py* (Linux A/B
safety: the lexical tiebreak still governs heuristic / Linux candidates, which
never carry a dlpfc_proposal_ref and so never get a dlpfc term).

These go through the real ``assess_candidates`` → ``select_allowed_assessment``
path; the Q5 audit confirmed producer→assess_candidates preserves the LLM's
emission order, so the loop index used for the rank IS the dlPFC preference.
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import Candidate, build_deliberation_input
from eva.l3_deliberation.peer_circuit.selection import select_allowed_assessment
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from scenarios.crafter import activate_crafter_scenario


def _raw_action_candidate(*, candidate_id: str, action: str, with_dlpfc_ref: bool = True) -> Candidate:
    """One Crafter raw-action candidate. All candidates built here share identical
    drive_impact_schema + gate fields, so drive/projection/experience terms are
    equal across them — the ONLY differentiator is the dlpfc_preference rank."""

    parameter_domain = {
        "candidate_kind": "raw_action",
        "raw_action_candidate": True,
        "candidate_profile": "crafter_raw_action",
        "turn_allowed": True,
        "instance_valid": True,
        "critical_blocked": False,
        "life_state": "STABLE",
        "conservative_mode": False,
        "compatibility_pressure_count": 0,
        "primary_pressure_reason": "none",
    }
    if with_dlpfc_ref:
        # The signal that marks this as a dlPFC-produced candidate (one shared
        # transcript ref per produce() call; identical string is fine — rank comes
        # from emission order, not from this value).
        parameter_domain["dlpfc_proposal_ref"] = "ofc_transcript::turn-0"
    return Candidate(
        candidate_id=candidate_id,
        capability="raw_action",
        action=action,
        parameter_domain=parameter_domain,
        justification=("crafter_llm_action_producer", f"action={action}", "domain_restricted"),
        drive_impact_schema={"metabolic": 0.2, "acquisition": 0.15},
        side_effect_class="crafter_raw_action",
    )


def _deliberation_input_with_threat():
    """A deliberation input with a threat signal so raw-action candidates pass the
    release-pressure gate (threat_count > 0) → disposition 'allow'. The threat
    raises score_delta identically for every candidate, so it does not perturb the
    equal-input premise."""

    return build_deliberation_input(
        {
            "signals": [{"class": "threat"}],
            "summary": {
                "signal_count": 1,
                "status_signal_count": 0,
                "threat_signal_count": 1,
                "background_signal_count": 0,
                "has_threat_signal": True,
            },
        },
        {
            "top_drive": "metabolic",
            "drive_levels": {
                "metabolic": 0.9,
                "safety": 0.4,
                "recovery": 0.3,
                "acquisition": 0.6,
                "capability": 0.5,
            },
            "drive_trends": {"metabolic": "stable"},
        },
        {
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


class DlpfcPreferenceSelectionTests(unittest.TestCase):
    """The capstone: dlpfc_preference order survives into selection, beating the
    alphabetical candidate_id tiebreak that caused the move_right bug."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        # LLM emission order = preference order. candidate_ids deliberately chosen
        # so the alphabetical MAX (what the old flat-tie path picked via max()) is
        # the LEAST-preferred (rank 2), not rank 0 — so a pass can only mean the
        # rank, not the id, decided selection.
        self.rank0 = _raw_action_candidate(candidate_id="candidate-crafter-do", action="do")
        self.rank1 = _raw_action_candidate(candidate_id="candidate-crafter-move-up", action="move_up")
        self.rank2 = _raw_action_candidate(candidate_id="candidate-crafter-place-stone", action="place_stone")
        # Sanity: rank2's id is the alphabetical max (the old-bug winner).
        ids = [self.rank0.candidate_id, self.rank1.candidate_id, self.rank2.candidate_id]
        assert max(ids) == self.rank2.candidate_id, "test premise: rank2 must be the lexical-max id"

    def test_rank0_wins_selection_over_alphabetical_max(self) -> None:
        assessments = assess_candidates([self.rank0, self.rank1, self.rank2], _deliberation_input_with_threat())
        allowed = [a for a in assessments if a.disposition == "allow"]
        # All three must be allowed for this to actually test the tiebreak.
        self.assertEqual(
            len(allowed), 3,
            f"setup expects all 3 raw-action candidates to allow; got {[(a.candidate_id, a.disposition) for a in assessments]}",
        )
        selected = select_allowed_assessment(assessments)
        self.assertIsNotNone(selected)
        self.assertEqual(
            selected.candidate_id,
            "candidate-crafter-do",
            "dlPFC rank-0 candidate must win selection. Old flat-tie behavior would "
            f"have picked the lexical-max id (rank2 place-stone); got {selected.candidate_id}.",
        )

    def test_scores_strictly_decrease_by_rank(self) -> None:
        assessments = assess_candidates([self.rank0, self.rank1, self.rank2], _deliberation_input_with_threat())
        by_id = {a.candidate_id: a for a in assessments}
        s0 = by_id["candidate-crafter-do"].score
        s1 = by_id["candidate-crafter-move-up"].score
        s2 = by_id["candidate-crafter-place-stone"].score
        # The flat tie is broken: rank0 > rank1 > rank2 purely from dlpfc_preference
        # (every other input is identical across the three).
        self.assertGreater(s0, s1)
        self.assertGreater(s1, s2)

    def test_dlpfc_term_recorded_in_decomposition(self) -> None:
        assessments = assess_candidates([self.rank0, self.rank1, self.rank2], _deliberation_input_with_threat())
        by_id = {a.candidate_id: a for a in assessments}
        decomp0 = by_id["candidate-crafter-do"].score_decomposition
        self.assertIsNotNone(decomp0)
        # rank 0 → W_DLPFC(0.3) * rank_value(1.0) = 0.3.
        self.assertAlmostEqual(decomp0.dlpfc_term, 0.3, places=6)

    def test_heuristic_candidate_gets_no_dlpfc_term(self) -> None:
        # A candidate WITHOUT a dlpfc_proposal_ref (heuristic / Linux) must get a
        # zero dlpfc term even when assessed alongside LLM candidates — Linux A/B
        # safety at the assess level (no LLM order → no preference signal).
        heuristic = _raw_action_candidate(
            candidate_id="candidate-crafter-noop", action="noop", with_dlpfc_ref=False
        )
        assessments = assess_candidates([heuristic], _deliberation_input_with_threat())
        decomp = assessments[0].score_decomposition
        self.assertIsNotNone(decomp)
        self.assertEqual(decomp.dlpfc_term, 0.0)


if __name__ == "__main__":
    unittest.main()
