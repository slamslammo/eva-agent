"""读取 EVA 运行时 append-only JSONL 文件的轻量工具。

设计目标：
- 容忍文件不存在（返回空列表）
- 容忍最后一行未完整写入（运行时正在 append 时，末行可能未 flush）
- 容忍非法 JSON 行（跳过，不抛错）
- 仅 stdlib，无第三方依赖

V0 实现：每次请求全量 re-read（runtime_dir 数据量 < 50MB 都能毫秒级返回）。
未来如需要可加 inotify / mtime 缓存优化。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    """读取一个 JSONL 文件，返回有效 JSON object 列表。

    容错策略：
    - 文件不存在 / 不是 file → 返回空列表
    - 空行 → 跳过
    - 末行未完整（运行时正在写）→ 跳过该行
    - 非 dict 顶层（例如 list 或 number）→ 跳过该行
    """

    p = Path(path)
    if not p.exists() or not p.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    # 末行未完整或行损坏；跳过
                    continue
                if isinstance(obj, dict):
                    entries.append(obj)
    except OSError:
        return []
    return entries


def read_jsonl_count(path: Path | str) -> int:
    """快速计算文件中的有效 JSONL 行数（用于增量轮询）。"""

    p = Path(path)
    if not p.exists() or not p.is_file():
        return 0
    count = 0
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except OSError:
        return 0
    return count
