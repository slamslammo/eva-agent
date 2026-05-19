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
    """Compact summary of one emitted signal batch by contract class.

    Round 1.B-4: ``threat_signal_count`` now narrows to imminent threats
    only (per scenario-declared ``imminent_threat_pressure_types``). The
    new ``pressure_signal_count`` covers non-imminent active pressures
    (metabolic / acquisition / capability / recovery for Crafter; non-
    integrity pressure types for Linux). Together they cover the same
    population the pre-1.B-4 ``threat_signal_count`` did.
    """

    signal_count: int
    status_signal_count: int
    threat_signal_count: int
    background_signal_count: int
    has_threat_signal: bool
    pressure_signal_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the batch summary for patrol and turn details."""

        return {
            "signal_count": self.signal_count,
            "status_signal_count": self.status_signal_count,
            "threat_signal_count": self.threat_signal_count,
            "background_signal_count": self.background_signal_count,
            "has_threat_signal": self.has_threat_signal,
            "pressure_signal_count": self.pressure_signal_count,
        }


def build_signal_batch_payload(signals: Sequence[SignalRecord]) -> dict[str, Any]:
    """Build the minimal B0 signal-batch payload for downstream readers."""

    return {
        "signals": [signal.to_dict() for signal in signals],
        "summary": summarize_signal_dispatch(signals).to_dict(),
    }


def build_patrol_signals(snapshot: ExternalLifeSnapshot, pressure_table: ActivePressureTable) -> list[SignalRecord]:
    """Build the minimal signal batch emitted by one completed patrol.

    Round 1.B-4: each active pressure is now classified as either an
    imminent threat (class="threat") or a general pressure
    (class="pressure") based on the active scenario's declared
    ``imminent_threat_pressure_types``. The pre-1.B-4 behavior
    indiscriminately emitted class="threat" for every pressure; that
    behavior is preserved as the fallback when no scenario is activated
    (e.g. low-level unit tests that bypass scenario_bundle).
    """

    signals = [build_status_signal(snapshot)]
    imminent_types = _imminent_threat_pressure_types()
    for pressure in pressure_table.pressures:
        # Legacy fallback (imminent_types is None) → all pressures emit
        # class="threat", preserving bit-equivalence with pre-1.B-4 callers
        # that do not activate a scenario bundle.
        is_imminent = imminent_types is None or pressure.type in imminent_types
        if is_imminent:
            signals.append(build_threat_signal(snapshot, pressure))
        else:
            signals.append(build_pressure_signal(snapshot, pressure))
    return signals


def _imminent_threat_pressure_types() -> frozenset[str] | None:
    """Resolve the active scenario's imminent-threat pressure type set.

    Returns ``None`` when no scenario is activated — caller treats that
    as legacy behavior (every pressure type counts as imminent). Returns
    a (possibly empty) ``frozenset`` when a scenario is active.
    """

    try:
        from ..scenario_bundle import get_active_runtime_scenario
        scenario = get_active_runtime_scenario()
    except Exception:
        # No scenario activated — preserve legacy "all pressures = threat"
        # semantic so low-level unit tests don't have to activate scenarios.
        return None
    declared = tuple(getattr(scenario.sensors, "imminent_threat_pressure_types", ()) or ())
    if not declared:
        # Scenario activated but didn't opt in. Preserve legacy by treating
        # every declared pressure type as imminent.
        return frozenset(scenario.sensors.pressure_types or ())
    return frozenset(declared)


def build_patrol_signal_artifacts(
    snapshot: ExternalLifeSnapshot,
    pressure_table: ActivePressureTable,
) -> tuple[list[SignalRecord], SignalDispatchSummary, dict[str, Any]]:
    """Build emitted signal records plus their frozen batch payload."""

    signals = build_patrol_signals(snapshot, pressure_table)
    signal_summary = summarize_signal_dispatch(signals)
    return signals, signal_summary, {
        "signals": [signal.to_dict() for signal in signals],
        "summary": signal_summary.to_dict(),
    }


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
    """Build one normalized threat signal from an imminent-threat pressure projection.

    Round 1.B-4: emitted only for pressure types the active scenario has
    declared as imminent (``imminent_threat_pressure_types``). For
    non-imminent active pressures, see ``build_pressure_signal``.
    """

    return SignalRecord(
        source=snapshot.source_patrol,
        signal_class="threat",
        payload=pressure.to_dict(),
        captured_at=snapshot.captured_at,
        rate_context=_rate_context_from_evidence(pressure.evidence),
    )


def build_pressure_signal(snapshot: ExternalLifeSnapshot, pressure: ActivePressure) -> SignalRecord:
    """Round 1.B-4: build one general-pressure signal from a non-imminent pressure.

    These signals still flow into deliberation (drive levels, candidate
    scoring) but do NOT trigger threat-response semantics in routing /
    curiosity suppression / memory salience. They represent ongoing
    pressures whose response should be deliberated rather than reflexed.
    """

    return SignalRecord(
        source=snapshot.source_patrol,
        signal_class="pressure",
        payload=pressure.to_dict(),
        captured_at=snapshot.captured_at,
        rate_context=_rate_context_from_evidence(pressure.evidence),
    )


def summarize_signal_dispatch(signals: Sequence[SignalRecord]) -> SignalDispatchSummary:
    """Summarize emitted signals by class for lightweight routing visibility."""

    status_signal_count = sum(1 for signal in signals if signal.signal_class == "status")
    threat_signal_count = sum(1 for signal in signals if signal.signal_class == "threat")
    background_signal_count = sum(1 for signal in signals if signal.signal_class == "background")
    pressure_signal_count = sum(1 for signal in signals if signal.signal_class == "pressure")
    return SignalDispatchSummary(
        signal_count=len(signals),
        status_signal_count=status_signal_count,
        threat_signal_count=threat_signal_count,
        background_signal_count=background_signal_count,
        has_threat_signal=threat_signal_count > 0,
        pressure_signal_count=pressure_signal_count,
    )


def _rate_context_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Extract one normalized rate-context payload when evidence provides it."""

    value = evidence.get("rate_context")
    if isinstance(value, dict):
        return dict(value)
    return {}
