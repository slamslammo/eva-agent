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

- **Status**: addressed (Round 1.C-2 / W6)
- **Why it matters**: Stage I 为让 working / episodic / semantic / procedural / inherited inputs 同时进入 working-memory 装配，扩展了若干参数与 payload 字段。当前复杂度仍在可接受范围内，但继续累加会提高 schema drift 与维护成本。
- **Resolution**: Round 1.C-2 在 `eva/l3_deliberation/reasoning/working_memory.py` 新增 `WorkingMemoryAssemblyLimits` dataclass，把四个 `max_*` output-size 参数收编为一个 limits 对象。`build_working_memory_context` 与 `build_working_memory_context_from_store` 接受可选的 `limits` 参数；为保持向后兼容，旧的单独 `max_*` kwargs 仍可使用——当二者同时出现时 `limits` 优先。数据源参数（`learning_outcomes` / `habit_bias_entries` / 等）保留为独立 kwargs 以方便测试注入。详见 `maintainer/development/round-1c-2-progress.md`。
