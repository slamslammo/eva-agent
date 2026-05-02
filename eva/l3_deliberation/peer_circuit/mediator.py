"""Default-inhibition mediator for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import CandidateAssessment, ReleaseDecision

__all__ = ["decide_release"]


def decide_release(assessments: list[CandidateAssessment]) -> ReleaseDecision:
    """Apply default inhibition and return one mediator decision."""

    allowed = [assessment for assessment in assessments if assessment.disposition == "allow"]
    if allowed:
        selected = max(
            allowed,
            key=lambda assessment: (
                round(assessment.score - assessment.learning_bias, 6),
                round(assessment.learning_bias, 6),
                assessment.score,
                assessment.candidate_id,
            ),
        )
        candidate_profile = _candidate_profile_from_id(selected.candidate_id)
        return ReleaseDecision(
            outcome="compatibility_release",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            release_context={
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": candidate_profile,
                "bridge_policy": _bridge_policy_for_candidate_profile(candidate_profile),
            },
            expected_outcome=_expected_outcome_for_candidate_profile(candidate_profile),
            learning_context={
                "candidate_profile": candidate_profile,
                "learning_bias": selected.learning_bias,
                "bias_reasons": list(selected.bias_reasons),
                "habit_narrowed": "habit_candidate_narrowing" in selected.reasons,
            },
        )

    deferred = [assessment for assessment in assessments if assessment.disposition == "defer"]
    if deferred:
        selected = deferred[0]
        return ReleaseDecision(
            outcome="defer",
            selected_action=selected.action,
            selected_candidate_id=selected.candidate_id,
            rationale=selected.reasons,
            expected_outcome="wait_for_safer_boundary",
            learning_context={
                "candidate_profile": _candidate_profile_from_id(selected.candidate_id),
                "learning_bias": selected.learning_bias,
                "bias_reasons": list(selected.bias_reasons),
                "habit_narrowed": "habit_candidate_narrowing" in selected.reasons,
            },
        )

    selected = assessments[0] if assessments else None
    return ReleaseDecision(
        outcome="withhold",
        selected_action=None,
        selected_candidate_id=None,
        rationale=() if selected is None else selected.reasons,
        expected_outcome="no_external_change",
        learning_context={} if selected is None else {
            "candidate_profile": _candidate_profile_from_id(selected.candidate_id),
            "learning_bias": selected.learning_bias,
            "bias_reasons": list(selected.bias_reasons),
            "habit_narrowed": "habit_candidate_narrowing" in selected.reasons,
        },
    )


def _candidate_profile_from_id(candidate_id: str | None) -> str:
    """Return the compact candidate profile name used by the compatibility bridge."""

    if candidate_id is None:
        return "unknown"
    if candidate_id.endswith("observe-first"):
        return "observe_first"
    if candidate_id.endswith("stabilize-first"):
        return "stabilize_first"
    return "unknown"


def _bridge_policy_for_candidate_profile(candidate_profile: str) -> dict[str, object]:
    """Return the explicit bridge policy derived from the selected internal profile."""

    applicability = {
        "pressure_reasons": ["recent_yield_detected"],
        "life_states": ["STABLE"],
    }
    if candidate_profile == "observe_first":
        return {
            "policy_name": "observe_first_bias",
            "selection": {
                "preferred_action": "recheck_runtime_integrity",
                "fallback_action": "escalate_integrity_risk",
                "default_path": "pressure_default",
            },
            "applicability": applicability,
            "execution": {
                "allow_repair_side_effects": False,
            },
        }
    if candidate_profile == "stabilize_first":
        return {
            "policy_name": "stabilize_first_bias",
            "selection": {
                "preferred_action": "shrink_to_conservative_mode",
                "fallback_action": "recheck_runtime_integrity",
                "default_path": "pressure_default",
            },
            "applicability": applicability,
            "execution": {
                "allow_repair_side_effects": True,
            },
        }
    return {
        "policy_name": "default_pressure_preference",
        "selection": {
            "preferred_action": "",
            "fallback_action": "",
            "default_path": "pressure_default",
        },
        "applicability": {},
        "execution": {
            "allow_repair_side_effects": True,
        },
    }


def _expected_outcome_for_candidate_profile(candidate_profile: str) -> str:
    """Return the minimal expected outcome label for one internal candidate profile."""

    if candidate_profile == "observe_first":
        return "improve_information_under_pressure"
    if candidate_profile == "stabilize_first":
        return "stabilize_or_relieve_pressure"
    return "bounded_pressure_response"
