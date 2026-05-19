"""Canonical goal-directed release-shaping helpers for the full deliberation path."""

from __future__ import annotations

from typing import Any

from ...scenario_bundle import get_active_runtime_scenario
from ..contracts import CandidateAssessment

__all__ = [
    "build_learning_context",
    "build_release_context",
    "candidate_profile_from_id",
    "expected_outcome_for_release",
]


def candidate_profile_from_id(candidate_id: str | None) -> str:
    """Return the compact candidate profile name used by peer-circuit downstreams."""

    if candidate_id is None:
        return "unknown"
    if candidate_id.endswith("observe-first"):
        return "observe_first"
    if candidate_id.endswith("stabilize-first"):
        return "stabilize_first"
    if candidate_id.endswith("escalate-first"):
        return "escalate_first"
    return "unknown"


def build_learning_context(assessment: CandidateAssessment) -> dict[str, Any]:
    """Build the shared learning-context payload from one selected assessment."""

    return {
        "candidate_profile": candidate_profile_from_id(assessment.candidate_id),
        "learning_bias": assessment.learning_bias,
        "bias_reasons": list(assessment.bias_reasons),
        "habit_narrowed": "habit_candidate_narrowing" in assessment.reasons,
    }


def build_release_context(
    candidate_profile: str,
    *,
    bridge_target: str = "pressure_led_compatibility",
    response_mode: str = "pressure_led_compatibility",
    working_memory_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the compatibility release-context payload for one candidate profile.

    Fix-2B: ``working_memory_context`` (when supplied) is folded into a
    ``bridge_policy["selection_context"]`` payload so scenario action
    bridges (e.g. ``select_response_action`` in Crafter) can honor habit
    bias, inherited prior bias, and situation_key. Without this plumbing
    the bridge had no access to working-memory at runtime and Round 1.A's
    selection-bias machinery was structurally written but never fed real
    inputs — producing the "candidates[0] always wins" behavior observed
    in Phase 1.5 v2.
    """

    bridge_policy = _bridge_policy_for_candidate_profile(candidate_profile)
    selection_context = _build_selection_context(working_memory_context)
    if selection_context:
        bridge_policy = dict(bridge_policy)
        bridge_policy["selection_context"] = selection_context
    return {
        "bridge_target": bridge_target,
        "response_mode": response_mode,
        "candidate_profile": candidate_profile,
        "bridge_policy": bridge_policy,
    }


def _build_selection_context(working_memory_context: dict[str, Any] | None) -> dict[str, Any]:
    """Extract a selection-context payload from working_memory_context.

    Returns a dict with keys consumed by ``select_response_action``-style
    scenario bridges: ``situation_key``, ``habit_summaries`` (from
    ``bias_summaries``), and ``inherited_priors``. Empty dict if no
    working_memory_context supplied.
    """

    if not isinstance(working_memory_context, dict):
        return {}
    payload: dict[str, Any] = {}
    situation_key = working_memory_context.get("situation_key")
    if isinstance(situation_key, str) and situation_key:
        payload["situation_key"] = situation_key
    bias_summaries = working_memory_context.get("bias_summaries")
    if isinstance(bias_summaries, list) and bias_summaries:
        payload["habit_summaries"] = list(bias_summaries)
    inherited_priors = working_memory_context.get("inherited_priors")
    if isinstance(inherited_priors, list) and inherited_priors:
        payload["inherited_priors"] = list(inherited_priors)
    return payload


def expected_outcome_for_release(outcome: str, candidate_profile: str | None) -> str:
    """Return the minimal expected-outcome label for one mediator outcome."""

    return get_active_runtime_scenario().outcome_observers.expected_outcome_for_release(outcome, candidate_profile)


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
    if candidate_profile == "escalate_first":
        return {
            "policy_name": "escalate_first_bias",
            "selection": {
                "preferred_action": "escalate_integrity_risk",
                "fallback_action": "recheck_runtime_integrity",
                "default_path": "pressure_default",
            },
            "applicability": {
                "pressure_reasons": ["runtime_files_missing", "runtime_not_writable", "recent_distress_detected"],
                "life_states": ["RECOVERING", "STABLE", "DEGRADED", "CRITICAL"],
            },
            "execution": {
                "allow_repair_side_effects": False,
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
