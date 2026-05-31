"""Drive ontology dataclasses (PR-Β §5.1).

A ``DriveOntologyEntry`` is the framework-level semantic record for one drive
type (``metabolic`` / ``safety`` / ``recovery`` / ``acquisition`` /
``capability`` / ``exploration``). It captures *meaning* (one-line semantics)
plus low/high anchor descriptions, scenario-bound typical_causes, and semantic
relief_directions (NOT hard policy).

``DriveOntology`` is the immutable container that the dlPFC prompt assembler
formats into the ``=== Drive Ontology ===`` system section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

__all__ = ["DriveOntologyEntry", "DriveOntology"]


@dataclass(frozen=True)
class DriveOntologyEntry:
    name: str
    meaning: str
    low_means: str
    high_means: str
    typical_causes: Sequence[str] = field(default_factory=tuple)
    relief_directions: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class DriveOntology:
    entries: tuple[DriveOntologyEntry, ...]

    def get(self, name: str) -> Optional[DriveOntologyEntry]:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def names(self) -> frozenset[str]:
        return frozenset(entry.name for entry in self.entries)

    def format_text(self) -> str:
        """Render the ontology as human-readable text for system prompt injection."""
        lines: list[str] = []
        for entry in self.entries:
            lines.append(f"{entry.name}:")
            lines.append(f"  meaning: {entry.meaning}")
            lines.append(f"  low_means: {entry.low_means}")
            lines.append(f"  high_means: {entry.high_means}")
            if entry.typical_causes:
                lines.append("  typical_causes:")
                for cause in entry.typical_causes:
                    lines.append(f"    - {cause}")
            if entry.relief_directions:
                lines.append("  relief_directions (semantic, not a hard policy):")
                for direction in entry.relief_directions:
                    lines.append(f"    - {direction}")
            lines.append("")
        return "\n".join(lines).rstrip()
