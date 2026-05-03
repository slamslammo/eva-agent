"""Read-only drive/candidate tension detection and structural conflict surfacing."""

from __future__ import annotations

from dataclasses import dataclass

from .candidate_generation import OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE
from ..contracts import Candidate

__all__ = [
    "CandidateConflictContext",
    "build_candidate_conflict_context",
]


@dataclass(frozen=True)
class CandidateConflictContext:
    """Normalized conflict/tension view for one candidate under current reasoning input."""

    candidate_profile: str
    disposition: str
    reasons: tuple[str, ...]
    score_delta: float = 0.0


def build_candidate_conflict_context(
    candidate: Candidate,
    *,
    top_drive: str,
    threat_count: int,
) -> CandidateConflictContext:
    """Return structural conflict and pressure-tension context for one candidate."""

    if candidate.action != "compatibility_release":
        return CandidateConflictContext(
            candidate_profile="unknown",
            disposition="withhold",
            reasons=("unknown_candidate_action",),
        )

    candidate_profile = str(candidate.parameter_domain.get("candidate_profile") or "unknown")
    if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=(f"candidate_profile={candidate_profile}", "unknown_candidate_profile"),
        )

    reasons = [f"candidate_profile={candidate_profile}"]
    turn_allowed = bool(candidate.parameter_domain.get("turn_allowed", False))
    instance_valid = bool(candidate.parameter_domain.get("instance_valid", False))
    critical_blocked = bool(candidate.parameter_domain.get("critical_blocked", False))
    life_state = str(candidate.parameter_domain.get("life_state") or "unknown")
    conservative_mode = bool(candidate.parameter_domain.get("conservative_mode", False))

    if not instance_valid:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "instance_not_valid"]),
        )
    if not turn_allowed:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "turn_not_allowed"]),
        )
    if critical_blocked:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "critical_runtime_boundary"]),
        )
    if life_state == "CRITICAL":
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "critical_life_state"]),
        )
    if conservative_mode:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "conservative_mode_active"]),
        )

    compatibility_pressure_count = int(candidate.parameter_domain.get("compatibility_pressure_count", 0))
    if top_drive != "integrity" and threat_count <= 0:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "no_release_pressure"]),
        )

    pressure_reasons = [*reasons, "integrity_or_threat_pressure_present"]
    score_delta = float(threat_count)
    if candidate_profile == STABILIZE_FIRST_PROFILE:
        if top_drive == "integrity":
            score_delta += 0.75
            pressure_reasons.append("integrity_bias_for_stabilize_first")
        if compatibility_pressure_count > 0:
            score_delta += 0.5
            pressure_reasons.append("pressure_bias_for_stabilize_first")
    elif candidate_profile == OBSERVE_FIRST_PROFILE:
        if top_drive != "integrity":
            score_delta += 0.25
            pressure_reasons.append("non_integrity_bias_for_observe_first")
        if compatibility_pressure_count == 0:
            score_delta += 0.25
            pressure_reasons.append("low_pressure_bias_for_observe_first")

    return CandidateConflictContext(
        candidate_profile=candidate_profile,
        disposition="allow",
        reasons=tuple(pressure_reasons),
        score_delta=score_delta,
    )
