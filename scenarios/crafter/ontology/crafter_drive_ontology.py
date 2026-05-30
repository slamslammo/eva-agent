"""Crafter drive ontology — DERIVED from CRAFTER_DRIVE_SPEC (single source).

single-source-scenario-drive-metadata: the drive ontology text is no longer a
second hardcoded copy. It is derived from ``CRAFTER_DRIVE_SPEC`` (the single
authority source shared with the drive preset), so the ontology and the preset
``drive_types`` can no longer drift apart.

Red line (plan §5.4.1): the semantic text is A-authored — B does NOT free-form.
The authored text now lives on ``CRAFTER_DRIVE_SPEC`` (scenarios/crafter/drive_spec.py);
any revision updates the plan first, then the spec. ``test_drive_spec_equivalence.py``
pins that this derived ontology is byte-identical to the pre-refactor text.
"""

from __future__ import annotations

from scenarios.crafter.drive_spec import CRAFTER_DRIVE_SPEC

__all__ = ["CRAFTER_DRIVE_ONTOLOGY"]


CRAFTER_DRIVE_ONTOLOGY = CRAFTER_DRIVE_SPEC.build_drive_ontology()
