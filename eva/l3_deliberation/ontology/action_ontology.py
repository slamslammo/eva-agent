"""Action ontology dataclasses (PR-Β §5.1).

``ActionOntologyEntry`` records the world-rule semantics of one raw action.
The ``effect`` field is a single-line summary; ``details`` is the bullet list
shown to the LLM. Optional ``typical_use`` is a parenthetical hint.

``ActionOntology`` is the container formatted into the
``=== Action Ontology ===`` system prompt section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

__all__ = ["ActionOntologyEntry", "ActionOntology"]


@dataclass(frozen=True)
class ActionOntologyEntry:
    action: str
    effect: str
    details: Sequence[str] = field(default_factory=tuple)
    typical_use: Optional[str] = None


@dataclass(frozen=True)
class ActionOntology:
    entries: tuple[ActionOntologyEntry, ...]

    def get(self, action: str) -> Optional[ActionOntologyEntry]:
        for entry in self.entries:
            if entry.action == action:
                return entry
        return None

    def actions(self) -> frozenset[str]:
        return frozenset(entry.action for entry in self.entries)

    def format_text(self) -> str:
        """Render the ontology for system prompt injection."""
        lines: list[str] = []
        for entry in self.entries:
            lines.append(f"{entry.action}:")
            lines.append(f"  effect: {entry.effect}")
            if entry.details:
                for detail in entry.details:
                    lines.append(f"  - {detail}")
            if entry.typical_use:
                lines.append(f"  typical use: {entry.typical_use}")
            lines.append("")
        return "\n".join(lines).rstrip()
