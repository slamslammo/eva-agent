"""Transitional bridge from current patrol judgment into pressure compatibility artifacts."""

from __future__ import annotations

from ..kernel import ActivePressure, ActivePressureTable, ExternalLifeSnapshot
from .pressure_projection import project_active_pressures


def build_active_pressure_table(
    snapshot: ExternalLifeSnapshot,
    previous_table: ActivePressureTable,
) -> tuple[ActivePressureTable, list[ActivePressure], list[ActivePressure]]:
    """Build the current pressure table and derive opened and resolved transitions."""

    current_pressures = project_active_pressures(snapshot, previous_table)
    previous_by_id = {pressure.pressure_id: pressure for pressure in previous_table.pressures}
    current_ids = {pressure.pressure_id for pressure in current_pressures}
    opened = [pressure for pressure in current_pressures if pressure.pressure_id not in previous_by_id]
    resolved = [pressure for pressure in previous_table.pressures if pressure.pressure_id not in current_ids]
    table = ActivePressureTable(
        captured_at=snapshot.captured_at,
        pressures=current_pressures,
        updated_at=snapshot.updated_at,
    )
    return table, opened, resolved


__all__ = ["build_active_pressure_table"]
