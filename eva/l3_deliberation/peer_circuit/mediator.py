"""Default-inhibition mediator for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import CandidateAssessment, ReleaseDecision, ReleaseToken
from .goal_directed_track import build_learning_context, build_release_context, candidate_profile_from_id, expected_outcome_for_release
from .selection import select_allowed_assessment, select_deferred_assessment, select_withhold_reference_assessment

__all__ = ["decide_release", "validate_release_token"]


def decide_release(assessments: list[CandidateAssessment]) -> ReleaseDecision:
    """Apply default inhibition and return one mediator decision."""

    selected = select_allowed_assessment(assessments)
    if selected is not None:
        candidate_profile = candidate_profile_from_id(selected.candidate_id)
        return ReleaseDecision(
            outcome="compatibility_release",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            release_context=build_release_context(candidate_profile),
            expected_outcome=expected_outcome_for_release("compatibility_release", candidate_profile),
            learning_context=build_learning_context(selected),
            release_token=ReleaseToken(
                token_id=_release_token_id(selected.candidate_id),
                outcome="compatibility_release",
                candidate_id=selected.candidate_id,
                candidate_profile=candidate_profile,
            ),
        )

    selected = select_deferred_assessment(assessments)
    if selected is not None:
        return ReleaseDecision(
            outcome="defer",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            expected_outcome=expected_outcome_for_release("defer", candidate_profile_from_id(selected.candidate_id)),
            learning_context=build_learning_context(selected),
        )

    selected = select_withhold_reference_assessment(assessments)
    return ReleaseDecision(
        outcome="withhold",
        selected_action=None,
        selected_candidate_id=None,
        rationale=() if selected is None else selected.reasons,
        expected_outcome=expected_outcome_for_release("withhold", None if selected is None else candidate_profile_from_id(selected.candidate_id)),
        learning_context={} if selected is None else build_learning_context(selected),
    )


def validate_release_token(
    release_token: ReleaseToken | None,
    *,
    selected_candidate_id: str | None,
    expected_outcome: str,
) -> None:
    """Validate runtime-only release authority before tool-edge execution."""

    if release_token is None:
        raise ValueError("release_token is required for mediated tool-edge execution")
    if release_token.outcome != expected_outcome:
        raise ValueError("release_token outcome is not executable")
    if selected_candidate_id is None or release_token.candidate_id != selected_candidate_id:
        raise ValueError("release_token candidate does not match selected candidate")
    if release_token.candidate_profile != candidate_profile_from_id(selected_candidate_id):
        raise ValueError("release_token profile does not match selected candidate")
    if release_token.token_id != _release_token_id(selected_candidate_id):
        raise ValueError("release_token id does not match selected candidate")


def _release_token_id(candidate_id: str) -> str:
    """Return a deterministic runtime token id for one selected candidate."""

    return f"release-token::{candidate_id}"
