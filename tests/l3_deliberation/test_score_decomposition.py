"""PR-Γ §6.1: ScoreDecomposition dataclass + CandidateAssessment field.

Tests cover:
- ScoreDecomposition is a frozen dataclass with 7 numeric fields + reasons tuple
- CandidateAssessment.score_decomposition default None (backward compat)
- assess_candidates populates score_decomposition with drive_weighted /
  projection_fallback / learning_bias / habit_priority_bonus / advisory /
  final_score values that match the existing CandidateAssessment.score

Red lines:
- existing CandidateAssessment.score / learning_bias / disposition / reasons
  unchanged (pure addition)
- score_decomposition.final_score should equal CandidateAssessment.score
- Linux byte-compat: callers constructing CandidateAssessment without the new
  field still work
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import (
    Candidate,
    CandidateAssessment,
    build_deliberation_input,
)
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from scenarios.linux_runtime import activate_linux_runtime_scenario


class ScoreDecompositionDataclassTests(unittest.TestCase):
    def test_score_decomposition_construction_and_field_access(self) -> None:
        from eva.l3_deliberation.contracts import ScoreDecomposition

        sd = ScoreDecomposition(
            drive_weighted=0.5,
            projection_fallback=0.1,
            learning_bias=0.05,
            habit_priority_bonus=0.02,
            semantic_overlay_blend=0.0,
            advisory=0.0,
            final_score=0.67,
            reasons=("top_drive=metabolic",),
        )
        self.assertEqual(sd.drive_weighted, 0.5)
        self.assertEqual(sd.projection_fallback, 0.1)
        self.assertEqual(sd.learning_bias, 0.05)
        self.assertEqual(sd.habit_priority_bonus, 0.02)
        self.assertEqual(sd.semantic_overlay_blend, 0.0)
        self.assertEqual(sd.advisory, 0.0)
        self.assertEqual(sd.final_score, 0.67)
        self.assertEqual(sd.reasons, ("top_drive=metabolic",))

    def test_score_decomposition_is_frozen(self) -> None:
        from eva.l3_deliberation.contracts import ScoreDecomposition

        sd = ScoreDecomposition(
            drive_weighted=0.0, projection_fallback=0.0, learning_bias=0.0,
            habit_priority_bonus=0.0, semantic_overlay_blend=0.0, advisory=0.0,
            final_score=0.0, reasons=(),
        )
        with self.assertRaises(Exception):
            sd.drive_weighted = 1.0  # type: ignore[misc]


class CandidateAssessmentScoreDecompositionFieldTests(unittest.TestCase):
    def test_default_score_decomposition_is_none(self) -> None:
        a = CandidateAssessment(
            candidate_id="c", action="noop", score=0.0,
            disposition="defer", reasons=(),
        )
        self.assertIsNone(a.score_decomposition)

    def test_assessment_carries_provided_score_decomposition(self) -> None:
        from eva.l3_deliberation.contracts import ScoreDecomposition

        sd = ScoreDecomposition(
            drive_weighted=0.4, projection_fallback=0.0, learning_bias=0.0,
            habit_priority_bonus=0.0, semantic_overlay_blend=0.0, advisory=0.0,
            final_score=0.4, reasons=(),
        )
        a = CandidateAssessment(
            candidate_id="c", action="noop", score=0.4,
            disposition="allow", reasons=("top_drive=metabolic",),
            score_decomposition=sd,
        )
        self.assertEqual(a.score_decomposition, sd)


class AssessCandidatesPopulatesScoreDecompositionTests(unittest.TestCase):
    """assess_candidates output now includes score_decomposition for every assessment."""

    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def _deliberation_input(self) -> object:
        return build_deliberation_input(
            {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
            {
                "top_drive": "safety",
                "drive_levels": {"safety": 0.8, "metabolic": 0.2, "recovery": 0.2,
                                 "acquisition": 0.2, "capability": 0.2, "exploration": 0.1},
                "drive_trends": {"safety": "stable"},
            },
            {
                "instance_valid": True, "turn_allowed": True,
                "critical_blocked": False, "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

    def test_every_assessment_has_score_decomposition_after_assess_candidates(self) -> None:
        di = self._deliberation_input()
        candidate = Candidate(
            candidate_id="c1",
            capability="compatibility",
            action="compatibility_release",
            parameter_domain={"candidate_profile": "observe_first", "habit_eligible": True},
        )
        assessments = assess_candidates([candidate], di)
        self.assertEqual(len(assessments), 1)
        sd = assessments[0].score_decomposition
        self.assertIsNotNone(sd, "assess_candidates must populate score_decomposition")
        # final_score must equal the assessment's score (single source of truth).
        self.assertEqual(sd.final_score, assessments[0].score)

    def test_score_decomposition_reasons_match_assessment_reasons(self) -> None:
        """ScoreDecomposition.reasons == assessment.reasons (no double-bookkeeping)."""
        di = self._deliberation_input()
        candidate = Candidate(
            candidate_id="c1", capability="compatibility", action="compatibility_release",
            parameter_domain={"candidate_profile": "observe_first", "habit_eligible": True},
        )
        assessments = assess_candidates([candidate], di)
        self.assertEqual(assessments[0].score_decomposition.reasons, assessments[0].reasons)


class CandidateAssessmentToDictIncludesDecompositionTests(unittest.TestCase):
    """to_dict should serialize the new field when present (additive)."""

    def test_to_dict_includes_score_decomposition_when_present(self) -> None:
        from eva.l3_deliberation.contracts import ScoreDecomposition

        sd = ScoreDecomposition(
            drive_weighted=0.4, projection_fallback=0.05, learning_bias=0.0,
            habit_priority_bonus=0.0, semantic_overlay_blend=0.0, advisory=0.0,
            final_score=0.45, reasons=("top_drive=metabolic",),
        )
        a = CandidateAssessment(
            candidate_id="c", action="noop", score=0.45,
            disposition="allow", reasons=("top_drive=metabolic",),
            score_decomposition=sd,
        )
        payload = a.to_dict()
        self.assertIn("score_decomposition", payload)
        decomp = payload["score_decomposition"]
        self.assertEqual(decomp["drive_weighted"], 0.4)
        self.assertEqual(decomp["final_score"], 0.45)

    def test_to_dict_omits_score_decomposition_when_none(self) -> None:
        """Backward compat: assessments without decomposition serialize the v1 way."""
        a = CandidateAssessment(
            candidate_id="c", action="noop", score=0.0,
            disposition="defer", reasons=(),
        )
        payload = a.to_dict()
        self.assertNotIn("score_decomposition", payload)


if __name__ == "__main__":
    unittest.main()
