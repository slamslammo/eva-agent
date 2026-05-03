"""Canonical append/read access helpers for append-only episodic memory artifacts."""

from __future__ import annotations

from typing import Any

from ...kernel import StateStore

__all__ = [
    "append_cognitive_memory_stub",
    "read_cognitive_memory_stub",
    "append_learning_outcome",
    "read_learning_outcomes",
    "append_habit_bias",
    "read_habit_bias",
]


def append_cognitive_memory_stub(store: StateStore, payload: dict[str, Any]) -> None:
    """Append one cognitive-memory stub through the episodic owner."""

    store.append_cognitive_memory_stub(payload)


def read_cognitive_memory_stub(store: StateStore) -> list[dict[str, Any]]:
    """Read cognitive-memory stubs through the episodic owner."""

    return store.read_cognitive_memory_stub()


def append_learning_outcome(store: StateStore, payload: dict[str, Any]) -> None:
    """Append one learning outcome through the episodic owner."""

    store.append_learning_outcome(payload)


def read_learning_outcomes(store: StateStore) -> list[dict[str, Any]]:
    """Read learning outcomes through the episodic owner."""

    return store.read_learning_outcomes()


def append_habit_bias(store: StateStore, payload: dict[str, Any]) -> None:
    """Append one habit-bias summary through the episodic owner."""

    store.append_habit_bias(payload)


def read_habit_bias(store: StateStore) -> list[dict[str, Any]]:
    """Read habit-bias summaries through the episodic owner."""

    return store.read_habit_bias()
