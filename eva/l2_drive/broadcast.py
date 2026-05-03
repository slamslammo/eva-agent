"""Canonical L2 broadcast projection owner."""

from __future__ import annotations

from dataclasses import dataclass

from ..kernel import DriveStateTable, to_iso8601
from .drive_state import summarize_drive_state


@dataclass(frozen=True)
class DriveBroadcast:
    """Canonical read-only L2 broadcast projection for downstream consumers."""

    captured_at: str | None
    updated_at: str | None
    top_drive: str
    top_level: float
    drive_levels: dict[str, float]
    drive_trends: dict[str, str]
    drives: dict[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        """Serialize the read-only broadcast view for downstream consumers."""

        return {
            "captured_at": self.captured_at,
            "updated_at": self.updated_at,
            "top_drive": self.top_drive,
            "top_level": self.top_level,
            "drive_levels": dict(self.drive_levels),
            "drive_trends": dict(self.drive_trends),
            "drives": {drive_type: dict(payload) for drive_type, payload in self.drives.items()},
        }


def build_drive_broadcast(table: DriveStateTable) -> DriveBroadcast:
    """Project the current drive table into the public read-only L2 broadcast view."""

    summary = summarize_drive_state(table)
    return DriveBroadcast(
        captured_at=to_iso8601(table.captured_at),
        updated_at=to_iso8601(table.updated_at),
        top_drive=summary.top_drive,
        top_level=summary.top_level,
        drive_levels=dict(summary.drive_levels),
        drive_trends={drive.drive_type: drive.trend for drive in table.drives},
        drives={
            drive.drive_type: {
                "level": drive.level,
                "delta": drive.delta,
                "trend": drive.trend,
                "contributors": list(drive.contributors),
                "updated_at": to_iso8601(drive.updated_at),
            }
            for drive in table.drives
        },
    )


__all__ = ["DriveBroadcast", "build_drive_broadcast"]
