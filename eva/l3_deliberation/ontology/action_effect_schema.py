"""Action × drive semantic effect schema (PR-Β §5.4.5).

The schema is a 2-D mapping ``matrix[action][drive] -> effect_label`` where the
effect label is drawn from the **semantic vocabulary** only (no graded
adverbs). Each cell expresses what world-rule + drive-definition derivation
says about the action's effect on that drive.

Per plan §5.4.5 boundary:
- ✅ may include: world rule + drive definition derivation
  (e.g. "move into water tile → restore water → metabolic relieved")
- ❌ must NOT include: graded estimates ("slightly improves", "often worsens")
- ❌ must NOT include: episodic memory ("usually water is in the southeast")

The schema does not duplicate world_facts (single source of truth) — it only
projects them onto drive dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

__all__ = ["ActionEffectSchema", "EFFECT_LABEL_VOCABULARY"]

# Canonical semantic effect labels. Compound labels ``improves_if_*`` /
# ``worsens_if_*`` are also valid (encoded by suffix), but must be a SINGLE
# clause without graded adverbs.
EFFECT_LABEL_VOCABULARY: frozenset[str] = frozenset({
    "improves",
    "worsens",
    "neutral",
    "context_dependent",
    "time_passes",
    # Conditional variants are also semantic (no degree word):
    "improves_if_sword",
    "worsens_if_threat_visible",
})


@dataclass(frozen=True)
class ActionEffectSchema:
    matrix: Mapping[str, Mapping[str, str]] = field(default_factory=dict)

    def effect(self, action: str, drive: str) -> Optional[str]:
        per_action = self.matrix.get(action)
        if per_action is None:
            return None
        return per_action.get(drive)

    def actions(self) -> frozenset[str]:
        return frozenset(self.matrix.keys())

    def drives(self) -> frozenset[str]:
        drives: set[str] = set()
        for per_action in self.matrix.values():
            drives.update(per_action.keys())
        return frozenset(drives)

    def format_text(self) -> str:
        """Render the matrix as text for system prompt injection."""
        lines: list[str] = []
        for action in sorted(self.matrix.keys()):
            lines.append(f"{action}:")
            per_action = self.matrix[action]
            for drive in sorted(per_action.keys()):
                lines.append(f"  {drive}: {per_action[drive]}")
            lines.append("")
        return "\n".join(lines).rstrip()
