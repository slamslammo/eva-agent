"""Rule-based value judgment for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

from .candidates import OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE
from .contracts import Candidate, CandidateAssessment, DeliberationInput


def assess_candidates(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[CandidateAssessment]:
    """Assess candidates using drive/signal pressure plus anchored runtime boundaries."""

    signal_summary = deliberation_input.signal_batch.get("summary", {})
    threat_count = int(signal_summary.get("threat_signal_count", 0))
    top_drive = str(deliberation_input.drive_broadcast.get("top_drive") or "unknown")

    assessments: list[CandidateAssessment] = []
    for candidate in candidates:
        reasons: list[str] = [f"top_drive={top_drive}"]
        score = 0.0
        turn_allowed = bool(candidate.parameter_domain.get("turn_allowed", False))
        instance_valid = bool(candidate.parameter_domain.get("instance_valid", False))
        critical_blocked = bool(candidate.parameter_domain.get("critical_blocked", False))
        life_state = str(candidate.parameter_domain.get("life_state") or "unknown")
        conservative_mode = bool(candidate.parameter_domain.get("conservative_mode", False))
        learning_bias = 0.0
        bias_reasons: list[str] = []
        if candidate.action == "compatibility_release":
            candidate_profile = str(candidate.parameter_domain.get("candidate_profile") or "unknown")
            compatibility_pressure_count = int(candidate.parameter_domain.get("compatibility_pressure_count", 0))
            reasons.append(f"candidate_profile={candidate_profile}")
            if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
                disposition = "withhold"
                reasons.append("unknown_candidate_profile")
            elif not instance_valid:
                disposition = "withhold"
                reasons.append("instance_not_valid")
            elif not turn_allowed:
                disposition = "withhold"
                reasons.append("turn_not_allowed")
            elif critical_blocked:
                disposition = "defer"
                reasons.append("critical_runtime_boundary")
            elif life_state == "CRITICAL":
                disposition = "defer"
                reasons.append("critical_life_state")
            elif conservative_mode:
                disposition = "defer"
                reasons.append("conservative_mode_active")
            elif top_drive == "integrity" or threat_count > 0:
                disposition = "allow"
                score = 1.0 + float(threat_count)
                reasons.append("integrity_or_threat_pressure_present")
                if candidate_profile == STABILIZE_FIRST_PROFILE:
                    if top_drive == "integrity":
                        score += 0.75
                        reasons.append("integrity_bias_for_stabilize_first")
                    if compatibility_pressure_count > 0:
                        score += 0.5
                        reasons.append("pressure_bias_for_stabilize_first")
                elif candidate_profile == OBSERVE_FIRST_PROFILE:
                    if top_drive != "integrity":
                        score += 0.25
                        reasons.append("non_integrity_bias_for_observe_first")
                    if compatibility_pressure_count == 0:
                        score += 0.25
                        reasons.append("low_pressure_bias_for_observe_first")
                learning_bias, bias_reasons = _learning_bias_for_candidate_profile(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                )
                score += learning_bias
            else:
                disposition = "withhold"
                reasons.append("no_release_pressure")
        else:
            disposition = "withhold"
            reasons.append("unknown_candidate_action")
        assessments.append(
            CandidateAssessment(
                candidate_id=candidate.candidate_id,
                action=candidate.action,
                score=round(score, 6),
                disposition=disposition,
                reasons=tuple(reasons),
                learning_bias=round(learning_bias, 6),
                bias_reasons=tuple(bias_reasons),
            )
        )
    return assessments


def _learning_bias_for_candidate_profile(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
) -> tuple[float, list[str]]:
    """Return the bounded learning bias for one candidate profile."""

    working_memory_context = deliberation_input.working_memory_context or {}
    bias_summaries = working_memory_context.get("bias_summaries")
    if not isinstance(bias_summaries, list):
        return 0.0, []
    for summary in bias_summaries:
        if str(summary.get("candidate_profile") or "") != candidate_profile:
            continue
        bias_strength = float(summary.get("bias_strength", 0.0))
        bounded_bias = max(-0.35, min(0.35, bias_strength * 0.25))
        if bounded_bias == 0.0:
            return 0.0, []
        reason = "positive_habit_bias" if bounded_bias > 0 else "negative_habit_bias"
        return bounded_bias, [reason]
    return 0.0, []
