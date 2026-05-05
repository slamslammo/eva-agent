"""Candidate generation for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import Candidate
from ...anchor.domain_restriction import (
    ActionDomain,
    COMPATIBILITY_RELEASE_IMPACT,
    ESCALATE_FIRST_PROFILE,
    OBSERVE_FIRST_PROFILE,
    STABILIZE_FIRST_PROFILE,
)


def build_candidates(action_domain: ActionDomain) -> list[Candidate]:
    """Build the minimal internal candidate set from admitted pre-generative schemas."""

    return [schema.to_candidate() for schema in action_domain.admitted_candidate_schemas]
