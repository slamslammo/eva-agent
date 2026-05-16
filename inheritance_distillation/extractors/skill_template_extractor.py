"""Skill-template extraction from deliberation audit traces."""

from __future__ import annotations

from typing import Any


def extract_skill_template_priors(bundle: dict[str, list[dict[str, Any]]], *, scenario: str) -> list[dict[str, Any]]:
    """Distill bounded candidate-shaping templates from deliberation audits."""

    records: list[dict[str, Any]] = []
    for audit in bundle.get("deliberation_audit.jsonl", []):
        if not isinstance(audit, dict):
            continue
        deliberation_input = audit.get("deliberation_input")
        if not isinstance(deliberation_input, dict):
            continue
        working_memory_context = deliberation_input.get("working_memory_context")
        if not isinstance(working_memory_context, dict):
            continue
        situation_key = str(working_memory_context.get("situation_key") or "")
        candidates = audit.get("candidates")
        if not situation_key or not isinstance(candidates, list):
            continue
        first_candidate = next((candidate for candidate in candidates if isinstance(candidate, dict)), None)
        if first_candidate is None:
            continue
        parameter_domain = first_candidate.get("parameter_domain")
        if not isinstance(parameter_domain, dict):
            continue
        candidate_profile = str(parameter_domain.get("candidate_profile") or "")
        preferred_action = str(parameter_domain.get("habit_preferred_action") or "")
        if not candidate_profile or not preferred_action:
            continue
        records.append(
            {
                "source": "distillation",
                "provenance_detail": "candidate_template_from_deliberation_audit",
                "confidence": 0.6,
                "scope": {
                    "scenario": scenario,
                    "situation_key": situation_key,
                    "extractor": "skill_template_extractor",
                },
                "content": {
                    "situation_key": situation_key,
                    "candidate_profile": candidate_profile,
                    "preferred_action": preferred_action,
                    "evidence_count": 1,
                    "stability_score": 0.6,
                    "bias_strength": 0.3,
                },
            }
        )
    return records
