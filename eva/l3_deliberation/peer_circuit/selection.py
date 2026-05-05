"""Canonical peer-circuit selection helpers for assessed candidates."""

from __future__ import annotations

from ..contracts import CandidateAssessment

__all__ = [
    "select_allowed_assessment",
    "select_deferred_assessment",
    "select_withhold_reference_assessment",
]


def select_allowed_assessment(assessments: list[CandidateAssessment]) -> CandidateAssessment | None:
    """Return the selected allowed assessment under current peer-circuit tie-breaking."""

    allowed = [assessment for assessment in assessments if assessment.disposition == "allow"]
    if not allowed:
        return None
    return max(allowed, key=_allowed_selection_key)



def select_deferred_assessment(assessments: list[CandidateAssessment]) -> CandidateAssessment | None:
    """Return the deferred assessment used when no release is authorized."""

    for assessment in assessments:
        if assessment.disposition == "defer":
            return assessment
    return None



def select_withhold_reference_assessment(assessments: list[CandidateAssessment]) -> CandidateAssessment | None:
    """Return the reference assessment used for withhold rationale and learning context."""

    return assessments[0] if assessments else None



def _allowed_selection_key(assessment: CandidateAssessment) -> tuple[float, float, float, str]:
    """Return the stable ranking key for allowed candidate selection."""

    return (
        round(assessment.score, 6),
        round(assessment.learning_bias, 6),
        assessment.score,
        assessment.candidate_id,
    )
