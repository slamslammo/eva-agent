"""Layer 1 sensing, judgment, cadence, and history projections."""

from .dimension_specs import DimensionSpec, get_default_dimension_specs, register_default_dimension_specs
from .history import build_pressure_event, build_survival_snapshot_entry, persist_patrol_artifacts
from .judgment import build_external_life_snapshot, determine_overall_status, determine_primary_gap, determine_trend, evaluate_dimensions
from .patrol import PATROL_ORDER, PATROL_INTERVAL_SECONDS, PatrolPlan, PatrolResult, PatrolScheduler, execute_patrol
from .routing import RoutingDecision, build_routing_decision
from .sensing import collect_external_life_inputs, default_sensor_registry
from .sensor_registry import SensingContext, SensorOutput, SensorRegistry, SensorSpec, build_sensor_registry
from .state_sensors import built_in_sensor_providers
from .signal_bus import SignalDispatchSummary, SignalRecord, build_patrol_signal_artifacts, build_patrol_signals, build_signal_batch_payload, summarize_signal_dispatch

__all__ = [
    "DimensionSpec",
    "PATROL_INTERVAL_SECONDS",
    "PATROL_ORDER",
    "PatrolPlan",
    "PatrolResult",
    "RoutingDecision",
    "SensingContext",
    "SensorOutput",
    "SensorRegistry",
    "SensorSpec",
    "SignalDispatchSummary",
    "SignalRecord",
    "build_external_life_snapshot",
    "build_routing_decision",
    "build_sensor_registry",
    "build_signal_batch_payload",
    "build_patrol_signal_artifacts",
    "build_survival_snapshot_entry",
    "built_in_sensor_providers",
    "collect_external_life_inputs",
    "default_sensor_registry",
    "determine_overall_status",
    "determine_primary_gap",
    "determine_trend",
    "evaluate_dimensions",
    "execute_patrol",
    "get_default_dimension_specs",
    "register_default_dimension_specs",
    "summarize_signal_dispatch",
]
