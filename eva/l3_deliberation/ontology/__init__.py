"""dlPFC ontology framework module (PR-Β).

Exposes the dataclasses + format helpers used to assemble the dlPFC system
prompt. Scenarios register their own ``DriveOntology`` / ``ActionOntology`` /
``ActionEffectSchema`` instances and the dlpfc producer composes them into a
single system prompt via ``build_dlpfc_system_prompt``.

PR-Β Slice 1 surface: dataclass exports only. Slice 2 will add
``ScenarioOntology`` + ``build_dlpfc_system_prompt`` + ``SalienceSpec`` +
``DlpfcRoleContract``.
"""

from __future__ import annotations

from .action_effect_schema import ActionEffectSchema, EFFECT_LABEL_VOCABULARY
from .action_ontology import ActionOntology, ActionOntologyEntry
from .dlpfc_role_contract import DlpfcRoleContract
from .drive_ontology import DriveOntology, DriveOntologyEntry
from .salience_spec import SalienceSpec
from .scenario_drive_spec import DriveSpecEntry, ScenarioDriveSpec
from .scenario_ontology import ScenarioOntology, build_dlpfc_system_prompt

__all__ = [
    "ActionEffectSchema",
    "ActionOntology",
    "ActionOntologyEntry",
    "DlpfcRoleContract",
    "DriveOntology",
    "DriveOntologyEntry",
    "DriveSpecEntry",
    "EFFECT_LABEL_VOCABULARY",
    "SalienceSpec",
    "ScenarioDriveSpec",
    "ScenarioOntology",
    "build_dlpfc_system_prompt",
]
