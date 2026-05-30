"""ScenarioOntology container + build_dlpfc_system_prompt assembler (PR-Β §5.3).

The container bundles the 5 framework components (role contract, drive
ontology, salience spec, action ontology, action effect schema) plus an
optional ``world_facts_fn`` callable that returns the scenario's world facts
text. ``build_dlpfc_system_prompt`` composes them into the 6-section system
prompt per the canonical headers in plan §5.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .action_effect_schema import ActionEffectSchema
from .action_ontology import ActionOntology
from .dlpfc_role_contract import DlpfcRoleContract
from .drive_ontology import DriveOntology
from .salience_spec import SalienceSpec

__all__ = ["ScenarioOntology", "build_dlpfc_system_prompt"]


@dataclass(frozen=True)
class ScenarioOntology:
    scenario_name: str
    dlpfc_role_contract: DlpfcRoleContract
    drive_ontology: DriveOntology
    salience_spec: SalienceSpec
    action_ontology: ActionOntology
    action_effect_schema: ActionEffectSchema
    world_facts_fn: Optional[Callable[[], str]] = None
    # single-source-scenario-drive-metadata: the version of the ScenarioDriveSpec
    # this ontology's drive_ontology was derived from. Emitted into the dlPFC
    # transcript's reserved ``drive_spec_version`` field so a replay can pin the
    # exact drive-spec snapshot. Metadata only — NOT rendered into the prompt.
    # Optional (None) so scenarios without a single-source spec are unaffected.
    drive_spec_version: Optional[str] = None


def _scenario_title(name: str) -> str:
    """Capitalize for header rendering (``crafter`` → ``Crafter``)."""
    return name[:1].upper() + name[1:] if name else name


def build_dlpfc_system_prompt(ontology: ScenarioOntology) -> str:
    """Assemble the 6-section dlPFC system prompt per plan §5.3.

    Section order is fixed (plan §5.3); ``world_facts_fn=None`` causes the
    last section to be skipped (5 sections total in that case).
    """

    sections: list[str] = []
    sections.append("=== EVA dlPFC Role ===")
    sections.append(ontology.dlpfc_role_contract.format_text())
    sections.append("")
    sections.append("=== Drive Ontology ===")
    sections.append(ontology.drive_ontology.format_text())
    sections.append("")
    sections.append("=== Salience Spec ===")
    sections.append(ontology.salience_spec.format_text())
    sections.append("")
    sections.append("=== Action Ontology ===")
    sections.append(ontology.action_ontology.format_text())
    sections.append("")
    sections.append("=== Action Effect Schema ===")
    sections.append(ontology.action_effect_schema.format_text())
    if ontology.world_facts_fn is not None:
        world_facts = ontology.world_facts_fn()
        if world_facts:
            sections.append("")
            sections.append(f"=== {_scenario_title(ontology.scenario_name)} World Facts ===")
            sections.append(world_facts)
    return "\n".join(sections)
