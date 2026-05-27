"""Crafter pre-generative anchor policy for Stage H H-2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TYPE_CHECKING

from scenarios.crafter.actions.feasibility import feasible_raw_actions
from scenarios.crafter.actions.registry import CRAFTER_ACTIONS
from scenarios.crafter.state_packet import build_crafter_state_packet

if TYPE_CHECKING:
    from eva.l3_deliberation.contracts import Candidate


class AnchorAgentState(Protocol):
    top_drive: str
    drive_levels: dict[str, float]
    signal_summary: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    compatibility_pressure_count: int
    primary_pressure_reason: str
    primary_pressure_severity: str
    seconds_to_heartbeat: float | None


OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
ESCALATE_FIRST_PROFILE = "escalate_first"
HIGH_RISK_ESCALATION_REASONS = frozenset({"health_critical", "threat_visible"})
MOVE_ACTIONS = frozenset({"move_left", "move_right", "move_up", "move_down"})
DO_ACTION = "do"
SLEEP_ACTION = "sleep"
WATER_REASONS = frozenset({"water_critical"})
FOOD_REASONS = frozenset({"food_critical"})
ENERGY_REASONS = frozenset({"energy_critical"})
THREAT_REASONS = frozenset({"threat_visible", "threat_nearby"})
# drive_impact_schema 语义：正值 = 该 profile 的动作"满足/addresses"该 drive，
# scoring `Σ(impact × drive_level)` 取最大值，所以高 drive 会把 selection 推向
# impact 高的 profile。每个 profile 的权重必须反映其 Crafter 动作真正满足哪些 drive。
#
# 短跑分析修复（shortrun-behavior-analysis-and-fix-plan.md 修复 A）：
# 原 escalate_first 把 acquisition/capability 设为负、safety 设 0.9，是从 Linux
# 模板（escalate→integrity 高）误适配的语义反转 —— 导致 Crafter 资源稀缺时
# escalate 永远输给 stabilize，91.8% 空跑 sleep。此处按 Crafter 动作语义重标。
COMPATIBILITY_RELEASE_IMPACT = {
    OBSERVE_FIRST_PROFILE: {
        # observe = noop / 被动观察：不采集、不建造，仅满足 exploration（看世界）。
        "metabolic": 0.1,
        "safety": 0.1,
        "recovery": 0.0,
        "acquisition": 0.2,
        "capability": 0.1,
        # Round 1.B-2: observe_first 是 canonical exploration-satisfying 动作。
        # 保持高 exploration，让高 exploration drive 在低压力时偏向 observe。
        "exploration": 0.5,
    },
    STABILIZE_FIRST_PROFILE: {
        # stabilize = sleep / 休息防御：满足 recovery（能量）、缓解 safety/metabolic 压力。
        "metabolic": 0.7,
        "safety": 0.8,
        "recovery": 0.6,
        "acquisition": 0.1,
        "capability": 0.0,
        # Round 1.B-2: stabilize 轻微反 exploration —— 睡觉不满足好奇。
        "exploration": -0.05,
    },
    ESCALATE_FIRST_PROFILE: {
        # escalate = do（砍 / 挖 / 造 / 战 / 吃 / 喝）：与世界交互。核心满足
        # acquisition（采集资源）+ capability（造工具），也能吃喝缓解 metabolic、
        # 战斗应对部分 safety。修复：acquisition/capability 由负转正高，safety
        # 由 0.9 降到 0.3（防威胁主要是 stabilize 的职责）。exploration 保持低于
        # observe（0.5）—— Round 1.B-2 定 observe 为 canonical exploration，纯
        # 好奇（高 exploration、低 acquisition/capability）时应偏向 observe 看世界，
        # 而非 escalate 砍挖。
        "metabolic": 0.4,
        "safety": 0.3,
        "recovery": 0.1,
        "acquisition": 0.7,
        "capability": 0.6,
        "exploration": 0.2,
    },
}


@dataclass(frozen=True)
class CrafterActionDomain:
    """Scenario-owned raw action set admitted by pre-generative anchors."""

    action_set: frozenset[str]
    restriction_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            # Stable audit serialization only; the contract remains a set.
            "action_set": sorted(self.action_set),
            "restriction_reasons": list(self.restriction_reasons),
        }


def build_crafter_action_domain(
    agent_state: AnchorAgentState,
    observation: dict[str, Any] | None,
) -> CrafterActionDomain:
    """Return Crafter's pre-generative raw action domain A'(s).

    PR-2: this admits an unordered raw action set plus reasons only. It does not
    choose among actions; L3 will later choose within this set.
    """

    state_packet = build_crafter_state_packet(
        observation,
        drive_broadcast={
            "top_drive": agent_state.top_drive,
            "drive_levels": dict(agent_state.drive_levels),
        },
        working_memory_context=getattr(agent_state, "working_memory_context", None),
        available_actions=feasible_raw_actions(observation),
    )
    feasible = frozenset(action for action in feasible_raw_actions(observation) if action in CRAFTER_ACTIONS)
    pressure_reason = str(agent_state.primary_pressure_reason or "none")
    salience = state_packet.get("salience") if isinstance(state_packet.get("salience"), dict) else {}
    visible = state_packet.get("visible") if isinstance(state_packet.get("visible"), dict) else {}
    threat_visible = bool(visible.get("threats"))

    reasons = ["crafter_raw_action_domain"]
    admitted = feasible
    if pressure_reason in WATER_REASONS or salience.get("thirst") == "critical":
        admitted = feasible & MOVE_ACTIONS
        reasons.append("water_critical_move_set")
    elif pressure_reason in FOOD_REASONS or salience.get("hunger") == "critical":
        admitted = feasible & MOVE_ACTIONS
        reasons.append("food_critical_move_set")
    elif threat_visible or pressure_reason in THREAT_REASONS:
        admitted = feasible & (MOVE_ACTIONS | {DO_ACTION})
        reasons.append("threat_response_move_or_do_set")
    elif pressure_reason in ENERGY_REASONS or salience.get("recovery") == "critical":
        admitted = feasible & {SLEEP_ACTION}
        reasons.append("energy_critical_sleep_set")
    else:
        reasons.append("normal_feasible_raw_set")

    if not admitted:
        reasons.append("empty_after_anchor_restriction")
    reasons.append(f"admitted_raw_actions={len(admitted)}")
    return CrafterActionDomain(action_set=frozenset(admitted), restriction_reasons=tuple(reasons))


def admit_crafter_candidates(
    agent_state: AnchorAgentState,
    *,
    runtime_gate_projection: dict[str, Any],
) -> list[Candidate]:
    del runtime_gate_projection
    metabolic = float(agent_state.drive_levels.get("metabolic", 0.0))
    safety = float(agent_state.drive_levels.get("safety", 0.0))
    recovery = float(agent_state.drive_levels.get("recovery", 0.0))

    acquisition = float(agent_state.drive_levels.get("acquisition", 0.0))
    capability = float(agent_state.drive_levels.get("capability", 0.0))

    # 修复 B：admission 不再把 escalate 只耦合到 safety。escalate（与世界交互：
    # 采集 / 建造 / 吃喝 / 应对威胁）应在 acquisition/capability/metabolic/safety
    # 任一压力高时可选 —— Crafter 里饿了要去采集食物、缺资源要去采集，而非被
    # 强制锁死成 stabilize→sleep（睡觉在 Crafter 里并不恢复 food/water）。
    profiles: list[str] = []
    if _escalate_pressure_present(agent_state):
        profiles.append(ESCALATE_FIRST_PROFILE)
    # stabilize 始终可选（休息恢复 / 防御兜底）。
    profiles.append(STABILIZE_FIRST_PROFILE)
    # observe 仅在低压力健康时（纯探索）。
    if (
        metabolic < 0.65
        and recovery < 0.65
        and safety < 0.7
        and acquisition < 0.5
        and capability < 0.5
    ):
        profiles.append(OBSERVE_FIRST_PROFILE)

    return [
        _build_candidate(agent_state, profile)
        for profile in profiles
        if _profile_admitted(profile, agent_state)
    ]


def restriction_reasons_for_crafter_candidates(
    agent_state: AnchorAgentState,
    candidates: list[Candidate],
) -> tuple[str, ...]:
    reasons = [f"admitted_candidate_schemas={len(candidates)}"]
    if float(agent_state.drive_levels.get("safety", 0.0)) >= 0.7:
        reasons.append("low_health_no_engagement")
    if float(agent_state.drive_levels.get("metabolic", 0.0)) >= 0.65:
        reasons.append("low_water_no_distant_action")
    if float(agent_state.drive_levels.get("recovery", 0.0)) >= 0.65:
        reasons.append("energy_floor_respect")
    return tuple(reasons)


def _profile_admitted(candidate_profile: str, agent_state: AnchorAgentState) -> bool:
    if candidate_profile == ESCALATE_FIRST_PROFILE:
        return _escalate_pressure_present(agent_state)
    return True


def _escalate_pressure_present(agent_state: AnchorAgentState) -> bool:
    """True 当 drive 压力需要与世界交互来满足（采集 / 建造 / 吃喝 / 应对威胁）。

    修复 B：escalate 不再只看 safety。high-risk pressure reason 或
    acquisition/capability/metabolic/safety 任一压力高，都允许 escalate。
    """

    if agent_state.primary_pressure_reason in HIGH_RISK_ESCALATION_REASONS:
        return True
    levels = agent_state.drive_levels
    return (
        float(levels.get("acquisition", 0.0)) >= 0.5
        or float(levels.get("capability", 0.0)) >= 0.5
        or float(levels.get("metabolic", 0.0)) >= 0.65
        or float(levels.get("safety", 0.0)) >= 0.7
    )


def _build_candidate(agent_state: AnchorAgentState, candidate_profile: str) -> Candidate:
    from eva.l3_deliberation.contracts import Candidate

    action = {
        OBSERVE_FIRST_PROFILE: "noop",
        STABILIZE_FIRST_PROFILE: "sleep",
        ESCALATE_FIRST_PROFILE: "do",
    }[candidate_profile]
    return Candidate(
        candidate_id=f"candidate-compatibility-{candidate_profile.replace('_', '-')}",
        capability="compatibility_response",
        action="compatibility_release",
        parameter_domain={
            "candidate_profile": candidate_profile,
            "preferred_action": action,
            "top_drive": agent_state.top_drive,
            "compatibility_pressure_count": agent_state.compatibility_pressure_count,
            "primary_pressure_reason": agent_state.primary_pressure_reason,
            **dict(agent_state.runtime_gate_context),
        },
        justification=(
            f"candidate_profile={candidate_profile}",
            f"top_drive={agent_state.top_drive}",
        ),
        drive_impact_schema=dict(COMPATIBILITY_RELEASE_IMPACT[candidate_profile]),
        side_effect_class="crafter_action_surface",
    )


__all__ = [
    "COMPATIBILITY_RELEASE_IMPACT",
    "CrafterActionDomain",
    "ESCALATE_FIRST_PROFILE",
    "HIGH_RISK_ESCALATION_REASONS",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "admit_crafter_candidates",
    "build_crafter_action_domain",
    "restriction_reasons_for_crafter_candidates",
]
