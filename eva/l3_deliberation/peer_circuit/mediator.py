"""Default-inhibition mediator for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import CandidateAssessment, ReleaseDecision, ReleaseToken
from .goal_directed_track import (
    build_learning_context,
    build_release_context,
    candidate_profile_from_assessment,
    expected_outcome_for_release,
)
from .selection import select_allowed_assessment, select_deferred_assessment, select_withhold_reference_assessment

__all__ = ["decide_release", "mint_reflex_release", "validate_release_token"]


def decide_release(
    assessments: list[CandidateAssessment],
    *,
    working_memory_context: dict[str, object] | None = None,
    anchor_domain_ref: str | None = None,
    dlpfc_proposal_ref: str | None = None,
) -> ReleaseDecision:
    """Apply default inhibition and return one mediator decision.

    Fix-2B: ``working_memory_context`` (optional) is propagated through to
    ``build_release_context`` so the resulting ``release_context`` carries
    a ``selection_context`` payload (habit / inherited-prior bias +
    situation_key). Scenario action bridges that consume
    ``release_context["bridge_policy"]["selection_context"]`` finally get
    real working-memory inputs in production runtime, not just in unit
    tests that fed the payload manually.

    PR-Α: ``anchor_domain_ref`` + ``dlpfc_proposal_ref`` (both optional, default
    ``None``) are embedded in the minted ``ReleaseToken`` so each release is
    back-traceable to its anchor domain and dlPFC LLM transcript. Defer/
    withhold paths do not mint tokens, so refs there are silently ignored.
    ``ofc_assessment_ref`` is reserved for PR-Γ and stays ``None`` here.
    """

    selected = select_allowed_assessment(assessments)
    if selected is not None:
        candidate_profile = candidate_profile_from_assessment(selected)
        return ReleaseDecision(
            outcome="compatibility_release",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            release_context=build_release_context(
                candidate_profile,
                working_memory_context=working_memory_context,
            ),
            expected_outcome=expected_outcome_for_release("compatibility_release", candidate_profile),
            learning_context=build_learning_context(selected),
            release_token=ReleaseToken(
                token_id=_release_token_id(selected.candidate_id),
                outcome="compatibility_release",
                candidate_id=selected.candidate_id,
                candidate_profile=candidate_profile,
                anchor_domain_ref=anchor_domain_ref,
                dlpfc_proposal_ref=dlpfc_proposal_ref,
                # ofc_assessment_ref left None — PR-Γ
            ),
        )

    selected = select_deferred_assessment(assessments)
    if selected is not None:
        candidate_profile = candidate_profile_from_assessment(selected)
        return ReleaseDecision(
            outcome="defer",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            expected_outcome=expected_outcome_for_release("defer", candidate_profile),
            learning_context=build_learning_context(selected),
        )

    selected = select_withhold_reference_assessment(assessments)
    candidate_profile = None if selected is None else candidate_profile_from_assessment(selected)
    return ReleaseDecision(
        outcome="withhold",
        selected_action=None,
        selected_candidate_id=None,
        rationale=() if selected is None else selected.reasons,
        expected_outcome=expected_outcome_for_release("withhold", candidate_profile),
        learning_context={} if selected is None else build_learning_context(selected),
    )


def mint_reflex_release(*, candidate_profile: str, rationale: tuple[str, ...] = ()) -> ReleaseDecision:
    """Mint a bounded mediator token for the threat reflex fast path."""

    selected_candidate_id = f"candidate-compatibility-{candidate_profile.replace('_', '-')}"
    return ReleaseDecision(
        outcome="compatibility_release",
        selected_action="compatibility_release",
        selected_candidate_id=selected_candidate_id,
        rationale=rationale,
        release_context=build_release_context(candidate_profile, bridge_target="l2_reflex", response_mode="protective_reflex"),
        expected_outcome=expected_outcome_for_release("compatibility_release", candidate_profile),
        learning_context={
            "candidate_profile": candidate_profile,
            "learning_bias": 0.0,
            "bias_reasons": [],
            "habit_narrowed": False,
        },
        release_token=ReleaseToken(
            token_id=_release_token_id(selected_candidate_id),
            outcome="compatibility_release",
            candidate_id=selected_candidate_id,
            candidate_profile=candidate_profile,
        ),
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
    if release_token.token_id != _release_token_id(selected_candidate_id):
        raise ValueError("release_token id does not match selected candidate")


def _release_token_id(candidate_id: str) -> str:
    """Return a deterministic runtime token id for one selected candidate."""

    return f"release-token::{candidate_id}"
