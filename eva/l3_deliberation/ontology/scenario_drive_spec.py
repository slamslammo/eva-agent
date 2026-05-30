"""ScenarioDriveSpec — single structured authority source for drive metadata.

The problem this solves (single-source-scenario-drive-metadata): a scenario's
drive *identity / semantics* used to live in two parallel hardcoded sources —
``DrivePreset.drive_types`` (+ ``drive_type_by_dimension`` + ``curiosity_drive_type``)
in ``drive_preset.py``, and the ``DriveOntologyEntry`` text in the scenario's
drive ontology module. Structural tests only caught cardinality drift (a drive
added to one but not the other); semantic drift (e.g. code drops ``energy`` from
``metabolic`` but the ontology text still claims it) slipped through.

``ScenarioDriveSpec`` makes a single declaration the authority. From it we derive:
- ``drive_types()`` and ``drive_type_by_dimension()`` and ``curiosity_drive_type()``
  → fed into ``DrivePreset`` (its *identity* fields; ``DriveUpdatePolicy`` behavior
  tuning stays authored on the preset and is intentionally NOT part of this spec)
- ``build_drive_ontology()`` → the ``DriveOntology`` consumed by the dlPFC prompt

Because both derivations read ``self.entries``, the ontology name set and the
preset ``drive_types`` can no longer disagree — the anti-drift guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .drive_ontology import DriveOntology, DriveOntologyEntry

__all__ = ["DriveSpecEntry", "ScenarioDriveSpec"]


@dataclass(frozen=True)
class DriveSpecEntry:
    """One drive's identity + semantics in the single authority source.

    ``name`` / ``meaning`` / ``low_means`` / ``high_means`` / ``typical_causes`` /
    ``relief_directions`` are the LLM-facing semantic fields (derived 1:1 into a
    ``DriveOntologyEntry``). ``dimensions`` lists the sensor dimensions routed to
    this drive (derived into ``drive_type_by_dimension``); an internal drive that
    no sensor feeds (e.g. a curiosity-updated exploration drive) declares ``()``.
    ``is_curiosity`` marks the single drive updated via the framework's
    curiosity recovery/suppression path (derived into ``curiosity_drive_type``).
    """

    name: str
    meaning: str
    low_means: str
    high_means: str
    typical_causes: tuple[str, ...] = ()
    relief_directions: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()
    is_curiosity: bool = False


@dataclass(frozen=True)
class ScenarioDriveSpec:
    """A scenario's authoritative drive-metadata declaration."""

    version: str
    entries: tuple[DriveSpecEntry, ...]

    def drive_types(self) -> tuple[str, ...]:
        """Drive names in declaration order (feeds ``DrivePreset.drive_types``)."""

        return tuple(entry.name for entry in self.entries)

    def drive_type_by_dimension(self) -> dict[str, str]:
        """Invert each entry's ``dimensions`` into a sensor-dimension → drive map.

        A drive may own multiple dimensions (each expands to its own entry); an
        entry with no dimensions contributes nothing. A sensor dimension must map
        to exactly one drive — declaring the same dimension on two drives is a
        construction error (raised here rather than silently resolved last-wins),
        since the resulting map would be ambiguous.
        """

        mapping: dict[str, str] = {}
        for entry in self.entries:
            for dimension in entry.dimensions:
                if dimension in mapping and mapping[dimension] != entry.name:
                    raise ValueError(
                        f"sensor dimension {dimension!r} is claimed by both "
                        f"{mapping[dimension]!r} and {entry.name!r}; each dimension "
                        f"must map to exactly one drive"
                    )
                mapping[dimension] = entry.name
        return mapping

    def curiosity_drive_type(self) -> str | None:
        """Return the single ``is_curiosity`` drive's name, or None if none.

        Declaring more than one curiosity drive is a construction error — the
        framework's curiosity update path targets exactly one drive type.
        """

        curiosity = [entry.name for entry in self.entries if entry.is_curiosity]
        if len(curiosity) > 1:
            raise ValueError(
                f"at most one drive may set is_curiosity=True; got {curiosity}"
            )
        return curiosity[0] if curiosity else None

    def build_drive_ontology(self) -> DriveOntology:
        """Derive the ``DriveOntology`` (LLM-facing text) from the same entries."""

        return DriveOntology(
            entries=tuple(
                DriveOntologyEntry(
                    name=entry.name,
                    meaning=entry.meaning,
                    low_means=entry.low_means,
                    high_means=entry.high_means,
                    typical_causes=tuple(entry.typical_causes),
                    relief_directions=tuple(entry.relief_directions),
                )
                for entry in self.entries
            )
        )
