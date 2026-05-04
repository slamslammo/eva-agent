"""Cross-layer anchor namespace for EVA structural restriction."""

from .cross_layer import apply_structural_anchors, build_action_domain
from .domain_restriction import ActionDomain, AgentState, CandidateSchema, restrict_candidate_domain

__all__ = [
    "ActionDomain",
    "AgentState",
    "CandidateSchema",
    "apply_structural_anchors",
    "build_action_domain",
    "restrict_candidate_domain",
]
