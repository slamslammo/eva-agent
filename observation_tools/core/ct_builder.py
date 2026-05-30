"""cognitive_trace 主轴的 TurnView 组装器（viz-p2 专用）。

设计：
- 以 cognitive_trace.jsonl 为主轴，按 turn_index 分组
- 对齐 raw_observations/{turn-NNNNNN.json} 游戏状态
- 对齐 llm_advisory_audit.jsonl
- 优雅处理任意文件缺失（返回 None 字段）
- warmup 判定：life_panel.available == False → is_warmup=True

仅 stdlib，无第三方依赖。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .trace_reader import read_jsonl


# cognitive_trace 各管道节点的 transform_id 前缀
_PIPELINE_TRANSFORMS = [
    "l1.raw_observation",
    "l1.threshold_classify",
    "l1.rate_sense",
    "l1.signal_publish",
    "l2.approach_delta",
    "l2.broadcast",
    "anchor.admit",
    "l3.candidate_produce",
    "l3.assess_score",
    "l3.decide_release",
    "mediator.release",
    "bridge.resolve_action",
]

# raw_observations 文件名格式
_RAW_OBS_FMT = "turn-{:08d}.json"

# LLM transcript 路径格式
_TRANSCRIPT_FMT = "llm_transcripts/dlPFC/turn-{:06d}.json"


@dataclass
class TurnView:
    """单个 turn 的完整视图。任意 None 字段表示该来源缺失。"""

    turn_index: int
    is_warmup: bool = False

    # L1 游戏状态（来自 raw_observations）
    game_state: dict[str, Any] | None = None

    # cognitive_trace 管道节点（按 transform_id 分组）
    pipeline: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # advisory（来自 llm_advisory_audit.jsonl）
    advisory: dict[str, Any] | None = None

    # LLM transcript（来自 llm_transcripts/dlPFC/，可选）
    transcript: dict[str, Any] | None = None

    # OFC 评分明细（来自 deliberation_audit.jsonl，Phase B）
    ofc_assessments: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "is_warmup": self.is_warmup,
            "game_state": self.game_state,
            "pipeline": self.pipeline,
            "advisory": self.advisory,
            "transcript": self.transcript,
            "ofc_assessments": self.ofc_assessments,
        }

    # ------------------------------------------------------------------
    # 便捷 accessor（前端常用字段，避免深层 JSON 导航）
    # ------------------------------------------------------------------

    @property
    def selected_action(self) -> str | None:
        nodes = self.pipeline.get("bridge.resolve_action") or []
        if nodes:
            return (nodes[-1].get("outputs") or {}).get("selected_action")
        nodes = self.pipeline.get("l3.decide_release") or []
        if nodes:
            return (nodes[-1].get("outputs") or {}).get("selected_action")
        return None

    @property
    def top_drive(self) -> str | None:
        nodes = self.pipeline.get("l2.broadcast") or []
        if nodes:
            return (nodes[-1].get("outputs") or {}).get("top_drive")
        return None

    @property
    def drive_levels(self) -> dict[str, float]:
        nodes = self.pipeline.get("l2.broadcast") or []
        if nodes:
            return (nodes[-1].get("outputs") or {}).get("drive_levels") or {}
        return {}

    @property
    def life_state(self) -> str:
        if self.is_warmup:
            return "warmup"
        if self.game_state:
            lp = self.game_state.get("life_panel") or {}
            vals = lp.get("values") or {}
            if vals:
                # 取最低值粗判断
                mn = min(vals.values())
                if mn <= 0:
                    return "critical"
                if mn <= 3:
                    return "stressed"
        return "normal"


def build_turn_views(runtime_dir: Path | str) -> list[TurnView]:
    """全量读取 cognitive_trace + raw_observations + advisory，组装 TurnView 列表。"""

    root = Path(runtime_dir)

    # 1. 读 cognitive_trace，按 turn_index 分组
    ct_records = read_jsonl(root / "cognitive_trace.jsonl")
    turn_map: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for rec in ct_records:
        idx = rec.get("turn_index")
        if idx is None:
            continue
        tid = rec.get("transform_id") or ""
        # 找对应的 pipeline key（l2.approach_delta 等前缀）
        key = _match_transform_key(tid)
        if key is None:
            continue
        turn_map.setdefault(idx, {}).setdefault(key, []).append(rec)

    # 2. 读 advisory，按行号对齐 turn_index
    advisories = read_jsonl(root / "llm_advisory_audit.jsonl")

    # 2b. 读 deliberation_audit（OFC 评分明细），按行号对齐 turn_index
    deliberations = read_jsonl(root / "deliberation_audit.jsonl")

    # 3. 确定 turn 数量（以 cognitive_trace 覆盖的最大 turn_index）
    if not turn_map:
        return []

    max_idx = max(turn_map.keys())
    views: list[TurnView] = []

    for idx in range(max_idx + 1):
        # 读游戏状态
        game_state = _read_game_state(root, idx)

        # warmup 判定
        is_warmup = False
        if game_state is not None:
            lp = game_state.get("life_panel") or {}
            if not lp.get("available", True):
                is_warmup = True
        elif idx < 2:
            # 保险：turn 0/1 没有 game state 时也视为 warmup
            is_warmup = True

        # 读 transcript（可选）
        transcript = _read_transcript(root, idx)

        ofc_assessments = None
        if idx < len(deliberations):
            asmt = deliberations[idx].get("assessments")
            if asmt:
                ofc_assessments = asmt

        view = TurnView(
            turn_index=idx,
            is_warmup=is_warmup,
            game_state=game_state,
            pipeline=turn_map.get(idx, {}),
            advisory=advisories[idx] if idx < len(advisories) else None,
            transcript=transcript,
            ofc_assessments=ofc_assessments,
        )
        views.append(view)

    return views


def build_timeline_v2(runtime_dir: Path | str) -> dict[str, Any]:
    """组装 timeline scrubber 所需精简数据（前端 /api/v2/timeline）。"""

    views = build_turn_views(runtime_dir)
    result: list[dict[str, Any]] = []
    for v in views:
        result.append({
            "turn_index": v.turn_index,
            "is_warmup": v.is_warmup,
            "action": v.selected_action,
            "top_drive": v.top_drive,
            "drive_levels": v.drive_levels,
            "life_state": v.life_state,
        })
    return {
        "n_turns": len(views),
        "turns": result,
    }


def build_run_info_v2(runtime_dir: Path | str) -> dict[str, Any]:
    """组装运行元信息（前端 /api/v2/run_info）。"""

    root = Path(runtime_dir)

    # 统计 turn 数
    ct_records = read_jsonl(root / "cognitive_trace.jsonl")
    turn_indices = {r.get("turn_index") for r in ct_records if r.get("turn_index") is not None}
    n_turns = len(turn_indices)

    # 检测各 artifact 是否存在
    has_transcripts = (root / "llm_transcripts" / "dlPFC").is_dir()
    has_deliberation_audit = (root / "deliberation_audit.jsonl").exists()
    has_advisory = (root / "llm_advisory_audit.jsonl").exists()

    run_name = root.parent.name or root.name

    return {
        "run_name": run_name,
        "runtime_dir": str(root),
        "n_turns": n_turns,
        "has_transcripts": has_transcripts,
        "has_deliberation_audit": has_deliberation_audit,
        "has_advisory": has_advisory,
        "artifacts_present": {
            "cognitive_trace": (root / "cognitive_trace.jsonl").exists(),
            "raw_observations": (root / "raw_observations").is_dir(),
            "llm_advisory_audit": has_advisory,
            "llm_transcripts_dlpfc": has_transcripts,
            "deliberation_audit": has_deliberation_audit,
        },
    }


# ------------------------------------------------------------------
# 内部辅助
# ------------------------------------------------------------------

def _match_transform_key(transform_id: str) -> str | None:
    """把 transform_id 映射到 pipeline key，None 表示不需要收录。"""
    for key in _PIPELINE_TRANSFORMS:
        if transform_id.startswith(key):
            return key
    return None


def _read_game_state(root: Path, idx: int) -> dict[str, Any] | None:
    """读单个 turn 的 raw_observation，提取游戏状态字段。"""
    fname = _RAW_OBS_FMT.format(idx)
    path = root / "raw_observations" / fname
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            rec = json.load(f)
        outputs = rec.get("outputs") or {}
        return {
            "local_view": outputs.get("local_view"),
            "life_panel": outputs.get("life_panel"),
            "inventory_panel": outputs.get("inventory_panel"),
            "facing": outputs.get("facing"),
            "step": outputs.get("step"),
            "episode_id": outputs.get("episode_id"),
        }
    except (OSError, json.JSONDecodeError):
        return None


def _read_transcript(root: Path, idx: int) -> dict[str, Any] | None:
    """读 dlPFC transcript（可选，文件不存在时返回 None）。"""
    path = root / _TRANSCRIPT_FMT.format(idx)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
