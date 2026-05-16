"""Pattern-oriented prior extraction from runtime traces."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

MIN_CONFIDENCE = 0.5
MIN_STABILITY = 0.5
MIN_EVIDENCE = 2


def extract_pattern_priors(bundle: dict[str, list[dict[str, Any]]], *, scenario: str) -> list[dict[str, Any]]:
    """Distill same-situation candidate regularities from learning outcomes."""

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in bundle.get("learning_outcomes.jsonl", []):
        if not isinstance(entry, dict):
            continue
        content = entry.get("content")
        if not isinstance(content, dict):
            continue
        situation_key = str(content.get("situation_key") or "")
        candidate_profile = str(entry.get("candidate_profile") or content.get("candidate_profile") or "")
        if not situation_key or not candidate_profile:
            continue
        grouped[(situation_key, candidate_profile)].append(entry)

    records: list[dict[str, Any]] = []
    for (situation_key, candidate_profile), entries in grouped.items():
        evidence_count = len(entries)
        if evidence_count < MIN_EVIDENCE:
            continue
        positive_count = sum(1 for entry in entries if float(entry.get("outcome_delta", 0.0)) > 0.0)
        support_ratio = positive_count / evidence_count
        confidence = round(max(float(entry.get("confidence", 0.0)) for entry in entries), 3)
        stability_score = round(support_ratio, 3)
        if confidence < MIN_CONFIDENCE or stability_score < MIN_STABILITY:
            continue
        preferred_action = _dominant_action(entries)
        if preferred_action is None:
            continue
        bias_strength = round(min(1.0, max(-1.0, ((support_ratio * 2.0) - 1.0))), 3)
        records.append(
            {
                "source": "distillation",
                "provenance_detail": "pattern_regularities_from_learning_outcomes",
                "confidence": confidence,
                "scope": {
                    "scenario": scenario,
                    "situation_key": situation_key,
                    "extractor": "pattern_extractor",
                },
                "content": {
                    "situation_key": situation_key,
                    "candidate_profile": candidate_profile,
                    "preferred_action": preferred_action,
                    "evidence_count": evidence_count,
                    "stability_score": stability_score,
                    "bias_strength": bias_strength,
                },
            }
        )
    return records


def _dominant_action(entries: list[dict[str, Any]]) -> str | None:
    action_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        action = str(entry.get("selected_action") or "")
        if action:
            action_counts[action] += 1
    if not action_counts:
        return None
    return sorted(action_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
