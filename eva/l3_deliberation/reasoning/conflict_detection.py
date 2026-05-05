"""Read-only drive/candidate tension detection and structural conflict surfacing."""

from __future__ import annotations

from dataclasses import dataclass

from .candidate_generation import ESCALATE_FIRST_PROFILE, OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE
from ..contracts import Candidate

DRIVE_CONFLICT_THRESHOLD = 0.5
SIGNIFICANT_IMPACT_THRESHOLD = 0.15

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
    drive_levels: dict[str, float] | None = None,
) -> CandidateConflictContext:
    """Return structural conflict and pressure-tension context for one candidate."""

    if candidate.action != "compatibility_release":
        return CandidateConflictContext(
            candidate_profile="unknown",
            disposition="withhold",
            reasons=("unknown_candidate_action",),
        )

    candidate_profile = str(candidate.parameter_domain.get("candidate_profile") or "unknown")
    if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE, ESCALATE_FIRST_PROFILE}:
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
    primary_pressure_reason = str(candidate.parameter_domain.get("primary_pressure_reason") or "none")
    if top_drive != "integrity" and threat_count <= 0:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "no_release_pressure"]),
        )

    pressure_reasons = [*reasons, "compatibility_projection_present"]
    score_delta = float(threat_count)
    if candidate_profile == STABILIZE_FIRST_PROFILE:
        if top_drive == "integrity":
            score_delta += 0.75
            pressure_reasons.append("integrity_projection_for_stabilize_first")
        if compatibility_pressure_count > 0:
            score_delta += 0.5
            pressure_reasons.append("pressure_projection_for_stabilize_first")
    elif candidate_profile == OBSERVE_FIRST_PROFILE:
        if top_drive != "integrity":
            score_delta += 0.25
            pressure_reasons.append("non_integrity_projection_for_observe_first")
        if compatibility_pressure_count == 0:
            score_delta += 0.25
            pressure_reasons.append("low_pressure_projection_for_observe_first")
    elif candidate_profile == ESCALATE_FIRST_PROFILE:
        if top_drive == "integrity":
            score_delta += 1.0
            pressure_reasons.append("integrity_projection_for_escalate_first")
        if primary_pressure_reason in {"runtime_files_missing", "runtime_not_writable", "recent_distress_detected"}:
            score_delta += 1.0
            pressure_reasons.append("high_risk_projection_for_escalate_first")
        if compatibility_pressure_count > 0:
            score_delta += 0.25
            pressure_reasons.append("pressure_projection_for_escalate_first")

    drive_tension_reasons = _drive_tension_reasons(
        candidate.drive_impact_schema,
        drive_levels=drive_levels or {},
    )
    for reason in drive_tension_reasons:
        if reason not in pressure_reasons:
            pressure_reasons.append(reason)

    return CandidateConflictContext(
        candidate_profile=candidate_profile,
        disposition="allow",
        reasons=tuple(pressure_reasons),
        score_delta=score_delta,
    )


def _drive_tension_reasons(
    drive_impact_schema: dict[str, float],
    *,
    drive_levels: dict[str, float],
) -> list[str]:
    """Return compact reasons when a candidate helps one high drive while harming another."""

    if not drive_impact_schema or not drive_levels:
        return []
    supported = [
        drive_name
        for drive_name, impact in drive_impact_schema.items()
        if impact >= SIGNIFICANT_IMPACT_THRESHOLD and float(drive_levels.get(drive_name, 0.0)) >= DRIVE_CONFLICT_THRESHOLD
    ]
    harmed = [
        drive_name
        for drive_name, impact in drive_impact_schema.items()
        if impact <= -SIGNIFICANT_IMPACT_THRESHOLD and float(drive_levels.get(drive_name, 0.0)) >= DRIVE_CONFLICT_THRESHOLD
    ]
    if not supported or not harmed:
        return []
    reasons = ["drive_tension_detected"]
    reasons.extend(f"supports_high_drive:{drive_name}" for drive_name in sorted(supported))
    reasons.extend(f"harms_high_drive:{drive_name}" for drive_name in sorted(harmed))
    return reasons
