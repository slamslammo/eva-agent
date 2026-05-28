"""Crafter scenario ontology package (PR-Β).

Bundles the 5 framework components (dlpfc_role_contract / drive_ontology /
salience_spec / action_ontology / action_effect_schema) plus the existing
world_facts callable into a single ``CRAFTER_SCENARIO_ONTOLOGY`` entry point
that the dlPFC producer consumes via ``build_dlpfc_system_prompt``.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import ScenarioOntology

from scenarios.crafter.world_facts import get_crafter_world_facts_context

from .crafter_action_effect_schema import CRAFTER_ACTION_EFFECT_SCHEMA
from .crafter_action_ontology import CRAFTER_ACTION_ONTOLOGY
from .crafter_dlpfc_role_contract import CRAFTER_DLPFC_ROLE_CONTRACT
from .crafter_drive_ontology import CRAFTER_DRIVE_ONTOLOGY
from .crafter_salience_spec import CRAFTER_SALIENCE_SPEC

__all__ = [
    "CRAFTER_ACTION_EFFECT_SCHEMA",
    "CRAFTER_ACTION_ONTOLOGY",
    "CRAFTER_DLPFC_ROLE_CONTRACT",
    "CRAFTER_DRIVE_ONTOLOGY",
    "CRAFTER_SALIENCE_SPEC",
    "CRAFTER_SCENARIO_ONTOLOGY",
]


CRAFTER_SCENARIO_ONTOLOGY = ScenarioOntology(
    scenario_name="crafter",
    dlpfc_role_contract=CRAFTER_DLPFC_ROLE_CONTRACT,
    drive_ontology=CRAFTER_DRIVE_ONTOLOGY,
    salience_spec=CRAFTER_SALIENCE_SPEC,
    action_ontology=CRAFTER_ACTION_ONTOLOGY,
    action_effect_schema=CRAFTER_ACTION_EFFECT_SCHEMA,
    world_facts_fn=get_crafter_world_facts_context,
)
