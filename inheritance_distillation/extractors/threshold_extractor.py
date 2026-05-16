"""Threshold-oriented prior extraction from habit-bias traces."""

from __future__ import annotations

from typing import Any


MIN_EVIDENCE = 2
MIN_CONFIDENCE = 0.5
MIN_STABILITY = 0.5


def extract_threshold_priors(bundle: dict[str, list[dict[str, Any]]], *, scenario: str) -> list[dict[str, Any]]:
    """Distill reusable habit-bias thresholds into inherited priors."""

    records: list[dict[str, Any]] = []
    for entry in bundle.get("habit_bias.jsonl", []):
        if not isinstance(entry, dict):
            continue
        situation_key = str(entry.get("situation_key") or "")
        candidate_profile = str(entry.get("candidate_profile") or "")
        evidence_count = int(entry.get("evidence_count", 0) or 0)
        confidence = round(float(entry.get("confidence", 0.0)), 3)
        stability_score = round(float(entry.get("stability_score", 0.0)), 3)
        if not situation_key or not candidate_profile:
            continue
        if evidence_count < MIN_EVIDENCE or confidence < MIN_CONFIDENCE or stability_score < MIN_STABILITY:
            continue
        preferred_action = entry.get("preferred_action")
        if preferred_action is None:
            continue
        records.append(
            {
                "source": "distillation",
                "provenance_detail": "threshold_habit_bias_summary",
                "confidence": confidence,
                "scope": {
                    "scenario": scenario,
                    "situation_key": situation_key,
                    "extractor": "threshold_extractor",
                },
                "content": {
                    "situation_key": situation_key,
                    "candidate_profile": candidate_profile,
                    "preferred_action": str(preferred_action),
                    "avoid_action": str(entry.get("avoid_action")) if entry.get("avoid_action") is not None else None,
                    "evidence_count": evidence_count,
                    "stability_score": stability_score,
                    "bias_strength": round(float(entry.get("bias_strength", 0.0)), 3),
                },
            }
        )
    return records
