"""按 turn 顺序把 EVA 多份 JSONL 输出对齐，组装成 ChainView 列表。

每个 ChainView 对应一次 turn 的完整链路：
    L1 signal_batch → L2 drive_broadcast → L3 deliberation
    → mediator release_decision → 动作执行 → outcome

主轴：``deliberation_audit.jsonl`` 的顺序索引即 ``turn_idx``。
其他来源（response_history / llm_advisory_audit / learning_outcomes / habit_bias）
按同序号对齐；某 turn 缺少某些来源时（运行末尾 off-by-one、文件缺失等）
graceful 退化为 None。

V0 实现：每次请求全量 build。对 211 turn × ~10KB JSON 数据集，毫秒级返回。
长跑（3000 turn × 10KB ≈ 30MB）也能在 100ms 内完成全量 read+组装。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .trace_reader import read_jsonl, read_jsonl_count


# 与 EVA 运行时 ``StateStore`` 写出的文件名对齐。
DELIBERATION_AUDIT_FILE = "deliberation_audit.jsonl"
RESPONSE_HISTORY_FILE = "response_history.jsonl"
LLM_ADVISORY_AUDIT_FILE = "llm_advisory_audit.jsonl"
LEARNING_OUTCOMES_FILE = "learning_outcomes.jsonl"
HABIT_BIAS_FILE = "habit_bias.jsonl"
SEMANTIC_MEMORY_FILE = "semantic_memory.jsonl"
EVENTS_FILE = "events.jsonl"


@dataclass(frozen=True)
class ChainView:
    """单个 turn 的"感知-决策-动作"完整链路视图。

    任意 None 字段表示该 turn 缺少对应来源（运行尚未产出、文件不存在、
    LLM advisory 未启用等）。
    """

    turn_idx: int                                   # 0-indexed
    recorded_at: str                                # 来自 deliberation_audit 的主时间戳
    deliberation: dict[str, Any] | None = None      # L1/L2/L3/mediator 完整链路
    response: dict[str, Any] | None = None          # 动作执行结果
    advisory: dict[str, Any] | None = None          # LLM advisory 调用
    outcome: dict[str, Any] | None = None           # RPE / learning outcome
    habit: dict[str, Any] | None = None             # habit_bias 当 turn 新增项

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_idx": self.turn_idx,
            "recorded_at": self.recorded_at,
            "deliberation": self.deliberation,
            "response": self.response,
            "advisory": self.advisory,
            "outcome": self.outcome,
            "habit": self.habit,
        }


def build_chains(runtime_dir: Path | str) -> list[ChainView]:
    """全量读取并组装 ChainView 列表。

    顺序：按 deliberation_audit 行号即 turn_idx。其他文件按相同序号对齐；
    某 turn 缺少对应来源（运行末尾 off-by-one 或文件不存在）时填 None。
    """

    root = Path(runtime_dir)

    deliberations = read_jsonl(root / DELIBERATION_AUDIT_FILE)
    responses = read_jsonl(root / RESPONSE_HISTORY_FILE)
    advisories = read_jsonl(root / LLM_ADVISORY_AUDIT_FILE)
    outcomes = read_jsonl(root / LEARNING_OUTCOMES_FILE)
    habits = read_jsonl(root / HABIT_BIAS_FILE)

    chains: list[ChainView] = []
    for idx, deliberation in enumerate(deliberations):
        chains.append(
            ChainView(
                turn_idx=idx,
                recorded_at=str(deliberation.get("recorded_at") or ""),
                deliberation=deliberation,
                response=responses[idx] if idx < len(responses) else None,
                advisory=advisories[idx] if idx < len(advisories) else None,
                outcome=outcomes[idx] if idx < len(outcomes) else None,
                habit=habits[idx] if idx < len(habits) else None,
            )
        )
    return chains


def build_timeline_summary(runtime_dir: Path | str) -> dict[str, Any]:
    """组装顶部迷你时间轴 + drive 折线所需的精简数据。

    返回结构（API ``/api/timeline`` 直接 jsonify）：

        {
            "n_turns": int,
            "turn_recorded_at": [str, ...],
            "life_state": [str, ...],           # 每 turn 的 life_state
            "drive_levels": {                   # 每 drive 一条折线序列
                "metabolic": [float, ...],
                "safety": [float, ...],
                ...
            },
            "advisory_outcomes": [str, ...],    # 每 turn 的 advisory.outcome（如有）
        }
    """

    root = Path(runtime_dir)
    deliberations = read_jsonl(root / DELIBERATION_AUDIT_FILE)
    responses = read_jsonl(root / RESPONSE_HISTORY_FILE)
    advisories = read_jsonl(root / LLM_ADVISORY_AUDIT_FILE)

    n_turns = len(deliberations)
    turn_recorded_at: list[str] = []
    life_states: list[str] = []
    drive_series: dict[str, list[float]] = {}
    advisory_outcomes: list[str] = []

    for idx, deliberation in enumerate(deliberations):
        turn_recorded_at.append(str(deliberation.get("recorded_at") or ""))

        resp = responses[idx] if idx < len(responses) else None
        life_states.append(str((resp or {}).get("life_state") or "UNKNOWN"))

        drive_broadcast = (
            (deliberation.get("deliberation_input") or {}).get("drive_broadcast") or {}
        )
        levels = drive_broadcast.get("drive_levels") or {}
        # 新 drive 进场：把它在过去 turn 的历史填 0
        for name in levels:
            if name not in drive_series:
                drive_series[name] = [0.0] * idx
        # 所有已注册的 drive：在本 turn 位置追加值（本 turn 缺失则填 0.0）
        for name in drive_series:
            drive_series[name].append(_safe_float(levels.get(name, 0.0)))

        adv = advisories[idx] if idx < len(advisories) else None
        advisory_outcomes.append(str((adv or {}).get("outcome") or ""))

    return {
        "n_turns": n_turns,
        "turn_recorded_at": turn_recorded_at,
        "life_state": life_states,
        "drive_levels": drive_series,
        "advisory_outcomes": advisory_outcomes,
    }


def runtime_counts(runtime_dir: Path | str) -> dict[str, int]:
    """返回 runtime_dir 下每个核心 JSONL 文件的行数。

    供 API ``/api/run_info`` 和前端轮询使用，便于"有新数据吗"判断。
    """

    root = Path(runtime_dir)
    return {
        "deliberation_audit": read_jsonl_count(root / DELIBERATION_AUDIT_FILE),
        "response_history": read_jsonl_count(root / RESPONSE_HISTORY_FILE),
        "llm_advisory_audit": read_jsonl_count(root / LLM_ADVISORY_AUDIT_FILE),
        "learning_outcomes": read_jsonl_count(root / LEARNING_OUTCOMES_FILE),
        "habit_bias": read_jsonl_count(root / HABIT_BIAS_FILE),
        "semantic_memory": read_jsonl_count(root / SEMANTIC_MEMORY_FILE),
        "events": read_jsonl_count(root / EVENTS_FILE),
    }


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
