"""Structural anchor restrictions for stable release boundaries."""

from __future__ import annotations

from ..l3_deliberation.contracts import Candidate, DeliberationInput


def apply_structural_anchor(candidate: Candidate, deliberation_input: DeliberationInput) -> Candidate:
    """Inject stable release-boundary constraints into one candidate domain."""

    runtime_gate = deliberation_input.runtime_gate_context
    restricted_domain = dict(candidate.parameter_domain)
    restricted_domain["instance_valid"] = bool(runtime_gate.get("instance_valid", False))
    restricted_domain["turn_allowed"] = bool(runtime_gate.get("turn_allowed", False))
    restricted_domain["critical_blocked"] = bool(runtime_gate.get("critical_blocked", False))
    return Candidate(
        candidate_id=candidate.candidate_id,
        capability=candidate.capability,
        action=candidate.action,
        parameter_domain=restricted_domain,
        justification=candidate.justification,
        drive_impact_schema=dict(candidate.drive_impact_schema),
        side_effect_class=candidate.side_effect_class,
    )


__all__ = ["apply_structural_anchor"]
