"""Linux runtime inherited-prior loading for Stage I I-4."""

from __future__ import annotations

from pathlib import Path

from eva.skills import InheritedPriorRegistry, load_inherited_prior_registry

from .compatibility import PRIOR_SKILL_MATCH_PROFILES

ALLOWED_ACTION_HINTS = frozenset({
    "recheck_runtime_integrity",
    "shrink_to_conservative_mode",
    "escalate_integrity_risk",
})


def build_linux_runtime_inherited_prior_registry(bundle_path: str | Path | None = None) -> InheritedPriorRegistry:
    """Load one Linux-runtime-only inherited-prior bundle into a framework registry."""

    return load_inherited_prior_registry(
        bundle_path=bundle_path,
        expected_scenario="linux_runtime",
        allowed_action_hints=ALLOWED_ACTION_HINTS,
        allowed_candidate_profiles=PRIOR_SKILL_MATCH_PROFILES,
        default_provenance_detail="linux_runtime_inherited_prior_bundle",
    )


__all__ = ["build_linux_runtime_inherited_prior_registry"]
