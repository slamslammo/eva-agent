"""Round 1.E — E-1 failing tests for the L3 reasoning proposal path (TDD red).

Pins the four invariants the proposer seam must satisfy (instruction §4 E-1):
  (a) under llm_assisted, the considered candidate set differs from local_rule_based;
  (b) an out-of-domain / malformed proposal is rejected + logged;
  (c) a high-confidence proposal is still gated by the mediator (authority holds);
  (d) default inhibition holds — the proposal path triggers no direct side effect.

These reference `eva.l3_deliberation.reasoning.proposer` (not yet implemented) and the
proposer-injecting `run_deliberation` signature, so the module is red until E-2..E-5 land.
The proposer only *shapes which candidates are considered* — selection (peer-circuit) and
release (mediator) authority are unchanged.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from eva.anchor import build_action_domain
from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.runtime import run_deliberation
from scenarios.crafter import activate_crafter_scenario

# E-1 is TDD-red: `reasoning.proposer` does not exist yet. Import defensively so
# the file still collects (the suite-wide regression runs); each test then fails
# explicitly until E-2..E-5 land the seam.
try:
    from eva.l3_deliberation.reasoning.proposer import (
        HeuristicProposer,
        ModelBackedProposer,
        ReasoningProposal,
        normalize_proposals,
    )

    _PROPOSER_READY = True
except ModuleNotFoundError:
    _PROPOSER_READY = False


def _deliberation_input(*, advisory_profiles=None, advisory_confidence=0.0, critical_blocked=False):
    """Build a minimal valid DeliberationInput, optionally with an LLM advisory_context."""

    signal_batch = {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}}
    drive_broadcast = {
        "top_drive": "acquisition",
        "drive_levels": {"acquisition": 0.8, "metabolic": 0.4, "safety": 0.3},
        "drive_trends": {"acquisition": "stable"},
    }
    runtime_gate_context = {
        "instance_valid": True,
        "turn_allowed": not critical_blocked,
        "critical_blocked": critical_blocked,
        "conservative_mode": False,
        "life_state": "STABLE",
    }
    working_memory_context = None
    if advisory_profiles is not None:
        working_memory_context = {
            "advisory_source": "llm_assisted",
            "advisory_context": {
                "candidate_suggestions": list(advisory_profiles),
                "prediction_hints": (),
                "reasoning_trace": ("test_advisory",),
                "confidence": advisory_confidence,
            },
        }
    return build_deliberation_input(
        signal_batch,
        drive_broadcast,
        runtime_gate_context,
        working_memory_context=working_memory_context,
    )


class ReasoningProposalPathTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)
        if not _PROPOSER_READY:
            self.fail("eva.l3_deliberation.reasoning.proposer not implemented yet (E-1 TDD red)")

    def test_model_proposer_changes_considered_set_vs_heuristic(self) -> None:
        # (a) The LLM-backed proposer, fed an advisory favoring escalate_first,
        # must shape a considered candidate set different from the deterministic
        # heuristic proposer (which ignores advisory).
        di_local = _deliberation_input()
        di_llm = _deliberation_input(advisory_profiles=["escalate_first"], advisory_confidence=0.9)
        domain_local = build_action_domain(di_local)
        domain_llm = build_action_domain(di_llm)

        heuristic = normalize_proposals(
            HeuristicProposer().propose(di_local.working_memory_context or {}, domain_local),
            domain_local,
        )
        model = normalize_proposals(
            ModelBackedProposer().propose(di_llm.working_memory_context or {}, domain_llm),
            domain_llm,
        )
        self.assertNotEqual(
            [c.candidate_id for c in heuristic.candidates],
            [c.candidate_id for c in model.candidates],
        )

    def test_out_of_domain_proposal_is_rejected_and_logged(self) -> None:
        # (b) A proposal naming a profile/action outside the anchor-admitted
        # domain must be dropped and recorded as a rejection (with a reason).
        domain = build_action_domain(_deliberation_input())
        bogus = ReasoningProposal(
            proposal_id="p-bogus",
            candidate_profile="attack_first",  # not in the 3-profile whitelist
            action_hint="nuke",
            predicted_outcome=None,
            rationale=("hallucinated",),
            confidence=0.99,
        )
        result = normalize_proposals([bogus], domain)
        self.assertNotIn("attack_first", [c.parameter_domain.get("candidate_profile") for c in result.candidates])
        rejected_ids = [r.get("proposal_id") for r in result.rejections]
        self.assertIn("p-bogus", rejected_ids)
        self.assertTrue(all(r.get("reason") for r in result.rejections))

    def test_high_confidence_proposal_is_still_gated_by_mediator(self) -> None:
        # (c) Even a max-confidence proposal cannot force release: under a
        # critical-blocked runtime gate the mediator must NOT emit a
        # compatibility_release. Authority stays with the mediator.
        di = _deliberation_input(
            advisory_profiles=["escalate_first"], advisory_confidence=1.0, critical_blocked=True
        )
        audit, _ = run_deliberation(self.now, di, proposer=ModelBackedProposer())
        self.assertNotEqual(audit.release_decision.get("outcome"), "compatibility_release")

    def test_reasoning_contribution_links_selected_candidate_to_proposal(self) -> None:
        # (E-6) When a proposer-shaped candidate is released, the audit records
        # which proposal produced it + that proposal's provenance — the
        # measurable reasoning-contribution signal.
        di = _deliberation_input(advisory_profiles=["escalate_first"], advisory_confidence=0.9)
        audit, _ = run_deliberation(self.now, di, proposer=ModelBackedProposer())
        if not audit.release_decision.get("selected_candidate_id"):
            self.skipTest("no candidate released for this input; contribution n/a")
        contribution = audit.reasoning_contribution
        self.assertIsNotNone(contribution)
        self.assertEqual(contribution["selected_candidate_id"], audit.release_decision.get("selected_candidate_id"))
        self.assertEqual(contribution["source_provenance"], "model_advisory")
        self.assertIn(contribution["source_proposal_id"], [p["proposal_id"] for p in audit.proposals])

    def test_proposal_path_has_default_inhibition(self) -> None:
        # (d) The proposer/normalization layer only produces candidates; it
        # exposes no selection/release surface and performs no side effect
        # (pure: repeated calls are equal, never auto-release).
        domain = build_action_domain(_deliberation_input())
        proposer = HeuristicProposer()
        self.assertFalse(hasattr(proposer, "release"))
        self.assertFalse(hasattr(proposer, "select"))
        first = normalize_proposals(proposer.propose({}, domain), domain)
        second = normalize_proposals(proposer.propose({}, domain), domain)
        self.assertEqual(
            [c.candidate_id for c in first.candidates],
            [c.candidate_id for c in second.candidates],
        )


if __name__ == "__main__":
    unittest.main()
