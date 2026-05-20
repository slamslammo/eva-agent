"""Active runtime scenario bundle and explicit activation seam."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .l1_sensing.dimension_specs import DimensionSpec

SensorSpecBuilder = Callable[[], tuple[Any, ...]]
SensorProviderFactory = Callable[[], tuple[SensorSpecBuilder, ...]]


@dataclass(frozen=True)
class SensorPolicyBundle:
    """Scenario-owned concrete sensor provider bundle.

    ``imminent_threat_pressure_types`` (Round 1.B-4): the subset of pressure
    types whose active pressures warrant the ``class="threat"`` signal
    classification — i.e. urgent / dangerous pressures that should suppress
    exploration drive, route through protective lanes, and amplify memory
    salience. Other active pressure types emit ``class="pressure"`` instead
    so they still influence drive levels and candidate scoring without
    triggering threat-response semantics. Default ``()`` keeps legacy
    behavior for scenarios that have not opted into the distinction.
    """

    sensor_providers: SensorProviderFactory
    dimension_specs: tuple["DimensionSpec", ...]
    pressure_types: tuple[str, ...]
    imminent_threat_pressure_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActionPolicyBundle:
    """Scenario-owned Step 2 action policy and executor bundle."""

    recheck_action: str
    repair_action: str
    escalate_action: str
    default_response_mode: str
    action_to_posture: dict[str, str]
    action_to_state_mode: dict[str, str]
    all_life_states: tuple[str, ...]
    action_to_allowed_states: dict[str, tuple[str, ...]]
    build_integrity_response_candidates: Callable[..., list[Any]]
    filter_response_candidates: Callable[..., list[Any]]
    select_integrity_response: Callable[..., Any]
    select_response_action: Callable[..., Any]
    execute_response_action: Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class AnchorPolicyBundle:
    """Scenario-owned anchor admission and reason policy bundle."""

    observe_first_profile: str
    stabilize_first_profile: str
    escalate_first_profile: str
    high_risk_escalation_reasons: frozenset[str]
    compatibility_release_impact: dict[str, dict[str, float]]
    admit_candidates: Callable[..., list[Any]]
    restriction_reasons_for_candidates: Callable[..., tuple[str, ...]]


@dataclass(frozen=True)
class OutcomeObserverBundle:
    """Scenario-owned outcome interpretation bundle."""

    expected_outcome_for_release: Callable[[str, str | None], str]
    evaluate_response_outcome: Callable[..., tuple[Any, ...]]
    build_learning_outcome_content: Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class PriorSkillBundle:
    """Scenario-owned prior-skill derivation and startup-prior inspection bundle."""

    habit_skill_match_for_candidate_profile: Callable[[str | None], bool]
    build_situation_key_from_values: Callable[..., str]
    derive_habit_skills: Callable[..., list[dict[str, Any]]]
    situation_key_from_learning_outcome: Callable[[dict[str, Any]], str]
    summarize_habit_bias: Callable[..., list[dict[str, Any]]]
    build_prior_skill_registry: Callable[..., Any]
    build_startup_prior_registry: Callable[[], Any]
    build_inherited_prior_registry: Callable[[str | Path | None], Any]


@dataclass(frozen=True)
class ExistenceSemantics:
    """场景声明的存在语义（v0.6 rev2）。

    rev2 把"什么算活 / 死"的解释权从框架交还场景：框架提供维持持续存在的机制 +
    七层分类语言，但不硬编码生死；它读取本声明并一致执行。**每个场景必须声明**。

    字段多为人类可读 / 审计用的声明（框架据此记录与校验）；``clock_source`` 是
    框架会主动消费的配置（决定生命时钟来源，见 rev2 决策点 3）。终止的实际**检测**
    发生在场景的 action_runtime（如 Crafter HP=0），由它向 kernel 报告 individual
    终止；本声明描述"规则是什么"，不替代行为。
    """

    # 什么算"还活着"（持续存在判据）
    continuity_criterion: str
    # 哪些中断算可恢复（重启 / 迁移 / 充电）；() = 无 in-life 可恢复中断（如单局 Crafter）
    recoverable_interruption: tuple[str, ...]
    # 什么算真死（不可恢复终止）
    terminal_failure: str
    # 一个 individual 的边界
    individual_boundary: str
    # reset 的语义："new_individual" / "same_individual_recovery" / "not_applicable"
    reset_semantics: str
    # 继承通道（有无 / 怎么蒸馏）
    inheritance_channel: str
    # 身份延续判据：重启 / 换 substrate 后，怎么算还是同一个 individual
    identity_continuity: str
    # 生命时钟来源（框架主动消费）："step"=回合驱动；"wall_clock"=挂钟秒
    clock_source: str = "wall_clock"


@dataclass(frozen=True)
class RuntimeScenarioBundle:
    """Full concrete scenario assembly activated for one runtime."""

    name: str
    drive_preset: Any
    sensors: SensorPolicyBundle
    actions: ActionPolicyBundle
    anchors: AnchorPolicyBundle
    outcome_observers: OutcomeObserverBundle
    prior_skills: PriorSkillBundle
    # v0.6 rev2: 每个场景必须声明存在语义（生死规则）。框架读取并一致执行。
    existence_semantics: ExistenceSemantics


_ACTIVE_RUNTIME_SCENARIO: RuntimeScenarioBundle | None = None


def activate_runtime_scenario(bundle: RuntimeScenarioBundle) -> RuntimeScenarioBundle:
    """Activate one scenario bundle for subsequent framework compatibility lookups."""

    from .l1_sensing.dimension_specs import register_default_dimension_specs

    global _ACTIVE_RUNTIME_SCENARIO
    _ACTIVE_RUNTIME_SCENARIO = bundle
    register_default_dimension_specs(tuple(bundle.sensors.dimension_specs), pressure_types=tuple(bundle.sensors.pressure_types))
    return bundle


def get_active_runtime_scenario() -> RuntimeScenarioBundle:
    """Return the active runtime scenario, requiring explicit activation first."""

    if _ACTIVE_RUNTIME_SCENARIO is None:
        raise RuntimeError(
            "no scenario activated; call activate_runtime_scenario() before using framework features that depend on scenario content"
        )
    return _ACTIVE_RUNTIME_SCENARIO


def get_active_existence_semantics() -> ExistenceSemantics:
    """Return the active scenario's existence-semantics declaration (v0.6 rev2)."""

    return get_active_runtime_scenario().existence_semantics


__all__ = [
    "ActionPolicyBundle",
    "AnchorPolicyBundle",
    "ExistenceSemantics",
    "OutcomeObserverBundle",
    "PriorSkillBundle",
    "RuntimeScenarioBundle",
    "SensorPolicyBundle",
    "activate_runtime_scenario",
    "get_active_existence_semantics",
    "get_active_runtime_scenario",
]
