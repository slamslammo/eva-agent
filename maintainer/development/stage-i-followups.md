# Stage I Follow-ups

本文档记录 **Stage I exit review sign-off** 后确认的非阻塞 follow-up。

## 1. Semantic memory 读路径需要 store-side windowing / indexing

- **Status**: resolved (Round 1.C-1 / W4)
- **Why it matters**: 当前 working-memory 装配会读取并扫描 `semantic_memory.jsonl`，在小规模数据下可接受，但随着 semantic 记忆累积，读放大和排序成本会逐步进入 deliberation 热路径。
- **Resolution**: Round 1.C-1 在 `eva/l3_deliberation/memory/semantic.py` 加入 process-local 内存索引（keyed on `StateStore.paths.runtime_dir`），消除每次 `read_semantic_memory` 调用的磁盘 re-read；并提供 `query_semantic_memory_for_situation(store, *, scenario, situation_key, top_drive, pressure_reason)` helper，基于倒排桶（`(scenario, situation_key) / (scenario, top_drive) / (scenario, pressure_reason) / topic / scenario`）返回候选 superset。append-only `.jsonl` artifact discipline 保持——索引纯派生于内存，未引入新持久化文件。详见 `maintainer/development/round-1c-1-progress.md`。

## 2. semantic memory → L2 drive weights 仍是显式 defer 项

- **Status**: resolved (Round 1.B-3 / W5)
- **Why it matters**: v0.6.1-rev1 §2.5 的集成表把 semantic memory 对 drive update weights 的影响列为目标能力。Stage I 为保留现有 drive-boundary invariant，合理地将其 defer，但这一项属于后续应继续兑现的理论承诺，而不是永久放弃。
- **Resolution**: Round 1.B-3 在 `eva/l3_deliberation/reasoning/value_judgment.py` 新增 `build_semantic_drive_impact_overlay`，并扩展 `_effective_drive_impact_schema` 在已有 learned overlay 之上叠加 semantic overlay。安全路径：`MAX_SEMANTIC_OVERLAY_BLEND=0.15`（小于 RPE/habit overlay 的 cap），`MIN_SEMANTIC_OVERLAY_CONFIDENCE=0.7`，只放大正向 impact，绝不削弱负向（不破坏安全/cost 信号），不动 drive_levels（drive read-only broadcast 保留）。详见 `maintainer/development/round-1b-3-progress.md`。

## 3. Working-memory 接口签名需要持续观察

- **Status**: watch
- **Why it matters**: Stage I 为让 working / episodic / semantic / procedural / inherited inputs 同时进入 working-memory 装配，扩展了若干参数与 payload 字段。当前复杂度仍在可接受范围内，但继续累加会提高 schema drift 与维护成本。
- **Current limitation**: `working_memory.py` 目前仍以多参数装配为主，接口数量和字段数已经接近应当复审的阈值。
- **Suggested direction**: 后续若继续扩展 working-memory 输入，优先先做接口签名 review；必要时再评估是否引入参数对象，而不是在 Stage I closeout 时顺手重构。
