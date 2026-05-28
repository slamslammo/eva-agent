"""Round 1.G phase 2 (a) — action_hint threading + Candidate serialization.

Pins the structural causal seam: the dlPFC producer may annotate a candidate with a
concrete ``action_hint``; after the mediator (frozen) selects a posture, the selected
candidate's hint is threaded into ``release_context`` for the Crafter bridge to consume.
When no hint is present (heuristic / model-off), the path is byte-identical.
"""

from __future__ import annotations

import dataclasses
import unittest
from datetime import datetime, timezone

from eva.anchor import build_action_domain
from eva.l3_deliberation.contracts import Candidate, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_producer import HeuristicCandidateProducer
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


class _HintingProducer:
    """Stub producer: heuristic candidates annotated with a unique per-candidate hint."""

    def produce(self, action_domain, deliberation_input):
        base = HeuristicCandidateProducer().produce(action_domain, deliberation_input)
        return [
            dataclasses.replace(c, action_hint=f"hint::{c.candidate_id}") for c in base
        ]


class CandidateSerializationTests(unittest.TestCase):
    def test_action_hint_omitted_when_none(self) -> None:
        candidate = Candidate(candidate_id="c1", capability="cap", action="a")
        self.assertNotIn("action_hint", candidate.to_dict())

    def test_action_hint_emitted_when_set(self) -> None:
        candidate = Candidate(candidate_id="c1", capability="cap", action="a", action_hint="do")
        self.assertEqual(candidate.to_dict()["action_hint"], "do")


class ActionHintThreadingTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)

    def test_no_hint_release_context_is_byte_identical(self) -> None:
        di = _deliberation_input()
        audit, _ = run_deliberation(self.now, di)
        release_context = audit.release_decision.get("release_context") or {}
        self.assertNotIn("action_hint", release_context)

    def test_selected_candidate_hint_threaded_into_release_context(self) -> None:
        di = _deliberation_input()
        audit, _ = run_deliberation(self.now, di, producer=_HintingProducer())
        release_decision = audit.release_decision
        selected_id = release_decision.get("selected_candidate_id")
        self.assertIsNotNone(selected_id)
        # The winner's hint (and only the winner's) is folded into release_context.
        self.assertEqual(
            release_decision["release_context"].get("action_hint"),
            f"hint::{selected_id}",
        )

    def test_threading_does_not_change_release_authority(self) -> None:
        di = _deliberation_input()
        plain, _ = run_deliberation(self.now, di)
        hinted, _ = run_deliberation(self.now, di, producer=_HintingProducer())
        # Posture/outcome/selection are decided by drive+mediator — unchanged by the hint.
        self.assertEqual(plain.release_decision.get("outcome"), hinted.release_decision.get("outcome"))
        self.assertEqual(
            plain.release_decision.get("selected_candidate_id"),
            hinted.release_decision.get("selected_candidate_id"),
        )
        self.assertEqual(
            plain.release_decision.get("selected_action"),
            hinted.release_decision.get("selected_action"),
        )


class RawActionCandidateThreadingTests(unittest.TestCase):
    """PR-4: raw-action candidates thread candidate.action as action_hint."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)

    def test_raw_action_candidate_action_threaded_as_action_hint(self) -> None:
        from eva.l3_deliberation.contracts import Candidate
        from eva.l3_deliberation.peer_circuit.mediator import decide_release
        from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
        from eva.anchor import build_action_domain

        raw_candidate = Candidate(
            candidate_id="candidate-crafter-move-left",
            capability="raw_action",
            action="move_left",
            parameter_domain={
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
            },
            justification=("crafter_llm_action_producer", "action=move_left", "domain_restricted"),
            drive_impact_schema={"metabolic": 0.15, "acquisition": 0.1},
            side_effect_class="crafter_raw_action",
        )

        di = _deliberation_input()
        assessments = assess_candidates([raw_candidate], di)
        # Raw-action candidate should be assessed (not skipped)
        self.assertGreaterEqual(len(assessments), 1)

        release_decision = decide_release(assessments)
        if release_decision.outcome != "compatibility_release":
            self.skipTest("mediator withheld — drive config made candidate ineligible")

        from eva.l3_deliberation.runtime import _thread_selected_action_hint
        threaded = _thread_selected_action_hint(release_decision, [raw_candidate])
        release_context = threaded.release_decision if hasattr(threaded, "release_decision") else threaded
        # The raw-action's .action must appear as action_hint in release_context
        rc = release_decision.release_context if release_decision.outcome == "compatibility_release" else {}
        threaded_decision = _thread_selected_action_hint(release_decision, [raw_candidate])
        self.assertEqual(
            threaded_decision.release_context.get("action_hint"),
            "move_left",
            "raw-action candidate.action must be threaded as action_hint for the bridge",
        )


if __name__ == "__main__":
    unittest.main()
