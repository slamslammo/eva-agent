"""Minimal cross-layer structural anchors for the Phase B / early Phase C skeleton."""

from __future__ import annotations

from ..l3_deliberation.contracts import Candidate, DeliberationInput

__all__ = ["apply_structural_anchors", "restrict_candidate_domain"]


def restrict_candidate_domain(candidate: Candidate, deliberation_input: DeliberationInput) -> Candidate:
    """Restrict one candidate's parameter domain using kernel/runtime boundaries."""

    runtime_gate = deliberation_input.runtime_gate_context
    restricted_domain = dict(candidate.parameter_domain)
    restricted_domain["instance_valid"] = bool(runtime_gate.get("instance_valid", False))
    restricted_domain["turn_allowed"] = bool(runtime_gate.get("turn_allowed", False))
    restricted_domain["critical_blocked"] = bool(runtime_gate.get("critical_blocked", False))
    restricted_domain["conservative_mode"] = bool(runtime_gate.get("conservative_mode", False))
    restricted_domain["life_state"] = runtime_gate.get("life_state")
    return Candidate(
        candidate_id=candidate.candidate_id,
        capability=candidate.capability,
        action=candidate.action,
        parameter_domain=restricted_domain,
        justification=candidate.justification,
    )


def apply_structural_anchors(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[Candidate]:
    """Apply the minimal anchor restriction pass to all candidates."""

    return [restrict_candidate_domain(candidate, deliberation_input) for candidate in candidates]
