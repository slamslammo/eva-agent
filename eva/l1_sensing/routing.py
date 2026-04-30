"""Minimal runtime-only L1 routing helpers layered on top of published signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .signal_bus import SignalRecord


@dataclass(frozen=True)
class RoutingDecision:
    """One bounded routing decision derived from a completed signal batch."""

    urgency: str
    dispatch_hint: str
    has_threat_signal: bool
    deliberation_allowed: bool
    compatibility_bridge_candidate: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the runtime-only routing decision for turn details."""

        return {
            "urgency": self.urgency,
            "dispatch_hint": self.dispatch_hint,
            "has_threat_signal": self.has_threat_signal,
            "deliberation_allowed": self.deliberation_allowed,
            "compatibility_bridge_candidate": self.compatibility_bridge_candidate,
            "reasons": list(self.reasons),
        }


def build_routing_decision(signals: Sequence[SignalRecord]) -> RoutingDecision:
    """Derive the minimal L1 dispatch semantics from a completed signal batch."""

    signal_list = list(signals)
    has_threat_signal = any(signal.signal_class == "threat" for signal in signal_list)
    if has_threat_signal:
        return RoutingDecision(
            urgency="high",
            dispatch_hint="protective_lane",
            has_threat_signal=True,
            deliberation_allowed=True,
            compatibility_bridge_candidate=True,
            reasons=("threat_signal_present",),
        )
    return RoutingDecision(
        urgency="normal",
        dispatch_hint="deliberation_only",
        has_threat_signal=False,
        deliberation_allowed=True,
        compatibility_bridge_candidate=False,
        reasons=_non_threat_reasons(signal_list),
    )


def _non_threat_reasons(signals: Sequence[SignalRecord]) -> tuple[str, ...]:
    """Explain why a non-threat signal batch stayed on the ordinary path."""

    if not signals:
        return ("no_signals",)
    signal_classes = {signal.signal_class for signal in signals}
    if signal_classes == {"background"}:
        return ("background_signal_only",)
    if "status" in signal_classes:
        return ("status_signal_present",)
    return ("non_threat_signal_present",)
