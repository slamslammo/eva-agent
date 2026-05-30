"""ScenarioActionSpec — single structured authority source for action metadata.

The action analogue of ScenarioDriveSpec (single-source-scenario-drive-metadata).
A scenario's raw-action *identity + semantics* used to live in two parallel
hardcoded sources — the ``ALL_ACTIONS`` name tuple (in actions/compatibility.py)
and the ``ActionOntologyEntry`` text (in the scenario's action ontology module).
A structural test caught cardinality drift but not semantic drift.

``ScenarioActionSpec`` makes one declaration the authority. From it we derive:
- ``action_names()`` → the raw-action name tuple (``ALL_ACTIONS``)
- ``build_action_ontology()`` → the ``ActionOntology`` consumed by the dlPFC prompt

Because both read ``self.entries``, the ontology action set and the name tuple
can no longer disagree. (The action × drive effect-schema's action axis is
pinned to this same name set by an axis-alignment test — see slice 3.)

Unlike a drive (which carries an engine-side ``dimensions`` mapping), a raw
action has no engine field beyond its name — the bridge/executor constants and
the ACTION_TO_* maps derive from the name tuple, not from this spec's semantics.
So ``ActionSpecEntry`` is purely name + LLM-facing semantics.
"""

from __future__ import annotations

from dataclasses import dataclass

from .action_ontology import ActionOntology, ActionOntologyEntry

__all__ = ["ActionSpecEntry", "ScenarioActionSpec"]


@dataclass(frozen=True)
class ActionSpecEntry:
    """One raw action's identity + LLM-facing semantics in the authority source.

    ``action`` is the raw action name (derived into the name tuple). ``effect`` /
    ``details`` / ``typical_use`` are the LLM-facing semantic fields (derived 1:1
    into an ``ActionOntologyEntry``).
    """

    action: str
    effect: str
    details: tuple[str, ...] = ()
    typical_use: str | None = None


@dataclass(frozen=True)
class ScenarioActionSpec:
    """A scenario's authoritative raw-action-metadata declaration."""

    version: str
    entries: tuple[ActionSpecEntry, ...]

    def action_names(self) -> tuple[str, ...]:
        """Raw action names in declaration order (feeds ``ALL_ACTIONS``).

        Action names must be unique — a duplicate is a construction error
        (ambiguous ontology / name set), raised here rather than silently
        de-duplicated.
        """

        names = tuple(entry.action for entry in self.entries)
        seen: set[str] = set()
        for name in names:
            if name in seen:
                raise ValueError(
                    f"duplicate action name {name!r}; each action must be declared once"
                )
            seen.add(name)
        return names

    def build_action_ontology(self) -> ActionOntology:
        """Derive the ``ActionOntology`` (LLM-facing text) from the same entries."""

        return ActionOntology(
            entries=tuple(
                ActionOntologyEntry(
                    action=entry.action,
                    effect=entry.effect,
                    details=tuple(entry.details),
                    typical_use=entry.typical_use,
                )
                for entry in self.entries
            )
        )
