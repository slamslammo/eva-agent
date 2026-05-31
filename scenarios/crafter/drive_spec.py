"""Crafter drive spec — the single authority source for Crafter drive metadata.

single-source-scenario-drive-metadata: this merges what used to be two parallel
hardcoded sources into one declaration:
- drive identity (drive_types / drive_type_by_dimension / curiosity_drive_type),
  previously hardcoded in ``drive_preset.py``
- drive semantics (meaning / low_means / high_means / typical_causes /
  relief_directions), previously hardcoded as ``DriveOntologyEntry`` text in
  ``ontology/crafter_drive_ontology.py``

``CRAFTER_DRIVE_PRESET`` (identity fields) and ``CRAFTER_DRIVE_ONTOLOGY`` are both
derived from ``CRAFTER_DRIVE_SPEC``, so they can no longer drift apart.

Red line (per plan §5.4.1): the semantic text is A-authored — B does NOT
free-form. This file is a 1:1 transcription/merge of the pre-existing
drive_preset.py + crafter_drive_ontology.py content (byte-equivalence pinned by
tests/scenarios/crafter/test_drive_spec_equivalence.py against the pre-refactor
oracle snapshot). Any future revision updates the plan first, then this file.

Behavior tuning (``DriveUpdatePolicy``) is intentionally NOT here — it stays
authored on the preset (spec = identity/semantics; policy = how-to-update).

Round 1.B-2 note (carried over): ``exploration`` is an *internal* drive — not
mapped to any sensor dimension (``dimensions=()``); it is updated through the
framework curiosity recovery/suppression path (``is_curiosity=True``), rising in
healthy/no-threat states and falling under threat/degraded status.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import DriveSpecEntry, ScenarioDriveSpec

__all__ = ["CRAFTER_DRIVE_SPEC"]


CRAFTER_DRIVE_SPEC = ScenarioDriveSpec(
    version="crafter-drive-spec-v1",
    entries=(
        DriveSpecEntry(
            name="metabolic",
            meaning="metabolic-resource pressure — the basic energy substances the body needs to keep running are under shortage pressure",
            low_means="metabolic resources sufficient, no shortage pressure",
            high_means="metabolic resources severely short, the individual is under metabolic pressure",
            typical_causes=(
                "food value dropping (hunger)",
                "water value dropping (thirst)",
                "energy value dropping (fatigue)",
                "health value dropping (injury)",
            ),
            relief_directions=(
                "walk into a water tile to refill water",
                "walk into a cow / plant tile to refill food",
                "sleep to recover energy (note: does NOT refill food/water)",
            ),
            dimensions=("avatar_metabolic",),
        ),
        DriveSpecEntry(
            name="safety",
            meaning="safety pressure — the degree to which the individual's survival is directly threatened by external threats",
            low_means="no visible threat currently, safe",
            high_means="a visible threat is approaching or has already caused harm",
            typical_causes=(
                "visible zombie / skeleton",
                "threat closing in",
                "night (zombies more frequent)",
            ),
            relief_directions=(
                "move away from threat",
                "attack the threat (do facing the threat tile, needs a sword)",
                "enter a safe area",
            ),
            # safety is fed by two sensor dimensions (avatar_safety + the
            # local_view threat channel).
            dimensions=("avatar_safety", "local_view_threat"),
        ),
        DriveSpecEntry(
            name="recovery",
            meaning="recovery-need pressure — the individual's energy reserve is in a state that needs active recovery",
            low_means="energy abundant, no need to rest",
            high_means="energy depleted, must rest to recover",
            typical_causes=(
                "energy value dropping",
                "no sleep for a long time",
            ),
            relief_directions=(
                "sleep action (but only in a safe environment)",
            ),
            dimensions=("avatar_recovery",),
        ),
        DriveSpecEntry(
            name="acquisition",
            meaning="resource-acquisition pressure — the individual currently lacks the basic resources needed to make progress",
            low_means="resources sufficient, no acquisition need",
            high_means="key resources missing, need to actively acquire",
            typical_causes=(
                "inventory empty / key resources (wood/stone/coal/iron) missing",
                "collectible resources seen nearby",
            ),
            relief_directions=(
                "move toward visible resources + do to collect",
                "explore unknown areas to find resources",
            ),
            # acquisition is fed by inventory + the local_view resource channel.
            dimensions=("inventory_acquisition", "local_view_resource"),
        ),
        DriveSpecEntry(
            name="capability",
            meaning="capability-building pressure — the individual currently lacks the capability tools needed to make progress",
            low_means="tools complete, capability meets the current task",
            high_means="key tools missing, constraining subsequent actions",
            typical_causes=(
                "no pickaxe (cannot mine)",
                "no sword (cannot attack threats)",
                "no table / furnace (cannot craft)",
            ),
            relief_directions=(
                "make_* / place_* after collecting materials",
                "craft prerequisite tools first (table → pickaxe → sword)",
            ),
            # capability is fed by inventory + the local_view utility channel.
            dimensions=("inventory_capability", "local_view_utility"),
        ),
        DriveSpecEntry(
            name="exploration",
            meaning="exploration drive — the individual's intrinsic pull to expand its cognitive boundary while healthy",
            low_means="low exploration intent (usually due to threat or resource pressure)",
            high_means="cognitive-expansion drive in a healthy state",
            typical_causes=(
                "rises naturally when currently safe + resources sufficient",
                "auto-suppressed under threat / resource pressure",
            ),
            relief_directions=(
                "head toward unexplored areas",
                "note: exploration is a growth-driver, not a must-resolve like the other drives",
            ),
            # internal growth-driver: no sensor dimension; curiosity-updated.
            dimensions=(),
            is_curiosity=True,
        ),
    ),
)
