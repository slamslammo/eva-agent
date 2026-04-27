"""Minimal signal publication contract and patrol-derived signal helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from ..kernel import ActivePressure, ActivePressureTable, ExternalLifeSnapshot, to_iso8601

SIGNAL_CLASSES = ("threat", "status", "background")


@dataclass(frozen=True)
class SignalRecord:
    """One normalized L1 signal that can flow into later routing layers."""

    source: str
    signal_class: str
    payload: dict[str, Any]
    captured_at: datetime
    rate_context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the signal using the frozen Phase A contract field names."""

        return {
            "source": self.source,
            "class": self.signal_class,
            "payload": self.payload,
            "captured_at": to_iso8601(self.captured_at),
            "rate_context": self.rate_context,
        }


@dataclass(frozen=True)
class SignalDispatchSummary:
    """Compact summary of one emitted signal batch by contract class."""

    signal_count: int
    status_signal_count: int
    threat_signal_count: int
    background_signal_count: int
    has_threat_signal: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize the batch summary for patrol and turn details."""

        return {
            "signal_count": self.signal_count,
            "status_signal_count": self.status_signal_count,
            "threat_signal_count": self.threat_signal_count,
            "background_signal_count": self.background_signal_count,
            "has_threat_signal": self.has_threat_signal,
        }


def build_patrol_signals(snapshot: ExternalLifeSnapshot, pressure_table: ActivePressureTable) -> list[SignalRecord]:
    """Build the minimal signal batch emitted by one completed patrol."""

    signals = [build_status_signal(snapshot)]
    for pressure in pressure_table.pressures:
        signals.append(build_threat_signal(snapshot, pressure))
    return signals


def build_status_signal(snapshot: ExternalLifeSnapshot) -> SignalRecord:
    """Build the one normalized status signal for a patrol snapshot."""

    return SignalRecord(
        source=snapshot.source_patrol,
        signal_class="status",
        payload=snapshot.to_dict(),
        captured_at=snapshot.captured_at,
        rate_context={
            dimension_name: _rate_context_from_evidence(dimension.evidence)
            for dimension_name, dimension in snapshot.dimensions.items()
        },
    )


def build_threat_signal(snapshot: ExternalLifeSnapshot, pressure: ActivePressure) -> SignalRecord:
    """Build one normalized threat signal from an active pressure projection."""

    return SignalRecord(
        source=snapshot.source_patrol,
        signal_class="threat",
        payload=pressure.to_dict(),
        captured_at=snapshot.captured_at,
        rate_context=_rate_context_from_evidence(pressure.evidence),
    )


def summarize_signal_dispatch(signals: Sequence[SignalRecord]) -> SignalDispatchSummary:
    """Summarize emitted signals by class for lightweight routing visibility."""

    status_signal_count = sum(1 for signal in signals if signal.signal_class == "status")
    threat_signal_count = sum(1 for signal in signals if signal.signal_class == "threat")
    background_signal_count = sum(1 for signal in signals if signal.signal_class == "background")
    return SignalDispatchSummary(
        signal_count=len(signals),
        status_signal_count=status_signal_count,
        threat_signal_count=threat_signal_count,
        background_signal_count=background_signal_count,
        has_threat_signal=threat_signal_count > 0,
    )


def _rate_context_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Extract one normalized rate-context payload when evidence provides it."""

    value = evidence.get("rate_context")
    if isinstance(value, dict):
        return dict(value)
    return {}
