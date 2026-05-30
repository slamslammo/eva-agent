"""Crafter action ontology — DERIVED from CRAFTER_ACTION_SPEC (single source).

single-source-crafter-action-metadata: the action ontology text is no longer a
second hardcoded copy. It is derived from ``CRAFTER_ACTION_SPEC`` (the single
authority shared with ``ALL_ACTIONS``), so the ontology and the raw-action name
tuple can no longer drift apart.

Red line (plan §5.4.4): the semantic text is A-authored — B does NOT free-form.
The authored text now lives on ``CRAFTER_ACTION_SPEC`` (scenarios/crafter/action_spec.py);
any revision updates the plan first, then the spec. ``test_action_spec_equivalence.py``
pins that this derived ontology is byte-identical to the pre-refactor text.
"""

from __future__ import annotations

from scenarios.crafter.action_spec import CRAFTER_ACTION_SPEC

__all__ = ["CRAFTER_ACTION_ONTOLOGY"]


CRAFTER_ACTION_ONTOLOGY = CRAFTER_ACTION_SPEC.build_action_ontology()
