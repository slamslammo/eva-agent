"""Risk-oriented prior extraction from deliberation and response traces."""

from __future__ import annotations

from typing import Any


def extract_risk_priors(bundle: dict[str, list[dict[str, Any]]], *, scenario: str) -> list[dict[str, Any]]:
    """Distill conservative avoidance hints from negative outcomes."""

    learning_by_audit: dict[str, dict[str, Any]] = {}
    for entry in bundle.get("learning_outcomes.jsonl", []):
        if not isinstance(entry, dict):
            continue
        linked = str(entry.get("linked_audit_recorded_at") or "")
        if linked:
            learning_by_audit[linked] = entry

    records: list[dict[str, Any]] = []
    for audit in bundle.get("deliberation_audit.jsonl", []):
        if not isinstance(audit, dict):
            continue
        audit_key = str(audit.get("recorded_at") or "")
        learning = learning_by_audit.get(audit_key)
        if learning is None or float(learning.get("outcome_delta", 0.0)) >= 0.0:
            continue
        content = learning.get("content")
        if not isinstance(content, dict):
            continue
        situation_key = str(content.get("situation_key") or "")
        candidate_profile = str(learning.get("candidate_profile") or content.get("candidate_profile") or "")
        selected_action = str(learning.get("selected_action") or "")
        if not situation_key or not candidate_profile or not selected_action:
            continue
        confidence = round(float(learning.get("confidence", 0.0)), 3)
        if confidence <= 0.0:
            continue
        records.append(
            {
                "source": "distillation",
                "provenance_detail": "negative_outcome_risk_pattern",
                "confidence": confidence,
                "scope": {
                    "scenario": scenario,
                    "situation_key": situation_key,
                    "extractor": "risk_extractor",
                },
                "content": {
                    "situation_key": situation_key,
                    "candidate_profile": candidate_profile,
                    "avoid_action": selected_action,
                    "evidence_count": 1,
                    "stability_score": 1.0,
                    "bias_strength": -1.0,
                },
            }
        )
    return records
