"""DlpfcRoleContract text container (PR-Β §5.4.3).

Defines the dlPFC role: position in the L1→L2→anchor→dlPFC→OFC→mediator→bridge
chain, do/don't/must-not list, and the allowed observation channel (canary).
The contract body is scenario-supplied (Crafter version in
``scenarios/crafter/ontology/crafter_dlpfc_role_contract.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["DlpfcRoleContract"]


@dataclass(frozen=True)
class DlpfcRoleContract:
    body: str

    def format_text(self) -> str:
        return self.body
