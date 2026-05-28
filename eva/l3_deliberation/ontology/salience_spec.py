"""SalienceSpec text container (PR-Β §5.4.2).

A frozen wrapper around the salience spec body so scenarios can register their
canonical text once and the assembler can format it without re-parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SalienceSpec"]


@dataclass(frozen=True)
class SalienceSpec:
    body: str

    def format_text(self) -> str:
        return self.body
