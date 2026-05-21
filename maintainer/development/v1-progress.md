# Phase 2 V1 — observation_tools Crafter plugin — 进展记录

> **本文件是主线侧对视觉线 V1 产出的 closeout 验收快照（历史记录）。**
> 视觉线的**活跃开发入口与章程**已迁移到 `observation_tools/dev/dev-guide.md`
> （随 viewer 代码一起 git 版本化，与主线 `maintainer/development/` 隔离）。
> 视觉迭代的新会话应读那份文档冷启动，不再在此继续维护。

**状态**：已完成（V1-a/b/c/d 全部落地）
**基础**：`observation_tools/`（V0 黑盒子查看器） + `validation-runs/phase1.7-live-smoke/runtime/`（211 turns 真实数据）

---

## 摘要

在 V0 的核心展示组件之上接入 **Crafter 场景特定 plugin**。把 EVA 运行时 trace 中场景特定的观察数据（生命体征 / 库存 / 工具 / 视野感知 / 维度状态 / 本 turn 变化）以专属面板形式渲染到右侧链路详情区，放在框架机制（L1 / L2 / L3 / mediator / 动作）section 之前。

主要发现：**EVA 运行时未持久化 agent observation**（9×7 grid 数据不在 trace），所以 V1 没做 grid 渲染。这部分留 V2，需要先在 runtime wrapper 加 observation 持久化 hook。但所有其他 Crafter 数据（vitals / inventory / local_view 统计 / capability_gap 等）都已经在 `signal_batch.payload.dimensions` 里，能完整提取。

---

## 子切片落地情况

### V1-a — Crafter extractor 后端

- 新增 `observation_tools/plugins/crafter/` 包（`__init__.py` + `extractor.py`）
- `extract_crafter_view(deliberation, response)` 从单 turn 数据提取 dict：
  - `vitals`：health / food / water / energy / threat_count（来自 `avatar_safety.evidence`）+ 三个 status (safety / metabolic / recovery)
  - `inventory`：items + tools + available_tools + key/scarce_resources（来自 `inventory_capability` + `inventory_acquisition`）
  - `local_view`：threat_total / resource_total / utility_total / scarce_resources / available_tools / capability_gap（来自三个 `local_view_*` dimension）
  - `rate_context`：health_direction / threat_count_direction / magnitude / acceleration（来自 `avatar_safety.evidence.rate_context`）
  - `deltas`：achievement_delta / life_delta / inventory_delta / visible_threat_count（来自 response_history）
  - `statuses`：8 个 dimension 的 status 一览
- 改造 `observation_tools/plugins/__init__.py` 提供 `apply_plugins_to_chain(chain_dict)` hook
- 改造 `observation_tools/core/chain_builder.py` 在 `ChainView.to_dict()` 时调用 hook
- 新增 12 个测试 `tests/observation_tools/test_crafter_extractor.py`（含 plugin hook 集成测试）

容错策略：deliberation 缺失 → 仅返回 deltas；response 缺失 → 仅返回 dimensions 数据；两者都缺 → 返回 None；signal_batch 中只有非 status 类 signal → 返回 None。

### V1-b — Crafter section 前端渲染

- `observation_tools/core/static/app.js` 增加 `renderCrafterSection(crafter)`（约 200 LOC，含 7 个辅助函数）：
  - 顶部 summary 徽章：`status · HP n · Food n · Water n · Energy n · Threats n`
  - 生命体征：4 条横向 bar（按值梯度着色：>=7 绿 / 4-6 黄 / 1-3 橙 / 0 红）+ rate_context 摘要
  - 库存：items grid（have/zero 区分）+ tools grid + 紧缺资源列表
  - 视野感知：threat / resource / utility / capability_gap 表
  - 本 turn 变化：achievement_delta / threat / life_delta / inventory_delta
  - 维度状态：8 个 dimension 的 status 徽章
- `observation_tools/core/static/style.css` 增加约 95 LOC 样式：
  - `.vital-row` / `.vital-bar-track` / `.vital-bar-fill`
  - `.inv-grid` / `.inv-item.have` / `.inv-item.zero` / `.inv-tool.*`
  - `.crafter-subhead` / `.status-row`
- 在 `renderDetail()` sections 列表中**Crafter section 放在 L1 之前**（场景观察先于框架机制）
- 加上首次加载默认选倒数第 2 个 turn 的逻辑（避免初始空详情区）

### V1-c — 启动 + 浏览器截图验证

- 启动 viewer：`python -m observation_tools --runtime-dir validation-runs/phase1.7-live-smoke/runtime --port 28391`（非常用端口避免冲突）
- Chrome 加载页面（通过 computer-use MCP 在 read tier 截图验证）
- 截图确认：
  - turn 列表正确（211 条倒序）
  - 时间轴 strip 显示 life_state segments + drive 折线
  - 默认选中 turn #209，右侧链路详情完整渲染
  - **Crafter section 完整渲染**：顶部摘要徽章 + 4 条生命 bar + 库存 + 工具 + 紧缺资源 + 视野感知表 + 本 turn 变化 + 8 个维度状态徽章
  - 下方 L1 / L2 / L3 等框架 section 正常
- 实测 chain dict 的 `crafter` 字段在 turn 100 数据齐全：vitals `{health:9, food:6, water:5, energy:9, threat_count:0}`、inventory 含 16 种 item 和 6 种 tool、local_view 含 6 种 scarce resource。

### V1-d — closeout

- 写 `maintainer/development/v1-progress.md`（本文件）
- 更新 `maintainer/development/current-intake.md` 标记 V1 完成
- 回归：**457 / 458 测试通过**（1 个 pre-existing `l2_drive` 失败，与 V1 无关）
- batch commit

---

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `observation_tools/plugins/crafter/__init__.py` | **新增**：plugin 入口 + 文档 |
| `observation_tools/plugins/crafter/extractor.py` | **新增**：约 130 LOC，提取 Crafter view dict |
| `observation_tools/plugins/__init__.py` | 改造：增加 `apply_plugins_to_chain()` hook |
| `observation_tools/core/chain_builder.py` | 在 `ChainView.to_dict()` 时调 plugin hook |
| `observation_tools/core/static/app.js` | 增加 `renderCrafterSection` + 默认 select 逻辑（约 +200 LOC） |
| `observation_tools/core/static/style.css` | 增加 Crafter 专用样式（约 +95 LOC） |
| `tests/observation_tools/test_crafter_extractor.py` | **新增**：12 个测试 |
| `maintainer/development/v1-progress.md` | **新增**：本文件 |
| `maintainer/development/current-intake.md` | 更新到 V1 完成态 |

---

## 回归 baseline

| 阶段 | 测试总数 | 通过 | 失败 | 备注 |
|---|---|---|---|---|
| V0 完成 | 446 | 445 | 1（pre-existing） | baseline |
| V1-a | 458 | 457 | 1（pre-existing） | +12 Crafter extractor 测试 |
| V1-b | 458 | 457 | 1（pre-existing） | 仅前端，无新测试 |
| V1-c | 458 | 457 | 1（pre-existing） | 仅手动 smoke |
| V1-d | 458 | 457 | 1（pre-existing） | 同上 |

唯一失败 `tests.l2_drive.test_drive.test_update_drive_state_accumulates_over_multiple_patrols` 在 `main` 上也存在，与 Phase 2 无关。

---

## 未做 / 推迟到 V2

- **9×7 local_view 彩色格子**：数据不在当前 trace（EVA 运行时未持久化 agent observation）。需要先改 `scenarios/crafter/wrapper/env_wrapper.py` 增加 observation 持久化 hook（每个 turn 把 `agent_observation.visible.local_view.cells` 写入 response_history 或独立文件）。改 runtime 代码超出 V1 "纯读工具" scope，留 V2。
- **跨 turn 趋势页**：原 dashboard 设计的 6 面板中真正"必看"的部分（drive 轨迹已经在顶部时间轴有了；其他面板等长跑数据出来再决定）。
- **Game replay 步进控制**：基础 ◀ ▶ ⏮ ⏭ + 速度选择 + scrubber。等场景数据更丰富（包含 9×7 grid）再做有意义。
- **多 run 切换**：UI 上下拉切换不同 runtime_dir。当前一次只能跑一个 run。
- **视觉整体优化**：用户已明确指出"整体视觉效果不好"。生命 bar 对比度低、时间轴折线对比度低、信息密度可以更高。等基于一个具体长跑跑起来再统一调整。

---

## V2 候选优先级（待长跑反馈调整）

按"对架构师理解 EVA 运作机制贡献最大"排序：

1. **整体视觉优化**：bar 对比度、徽章颜色、时间轴层次（用户已点名）
2. **9×7 local_view 格子**：让"agent 看到什么"具象化（需 runtime 增 observation 持久化）
3. **跨 turn 链路演化的对比视图**：例如选两个 turn 并排展开
4. **events.jsonl 集成**：把 tick/turn/distress 事件挂在时间轴上
5. **achievement 解锁标记**：哪些 turn 解锁了什么成就（在时间轴上点亮）
6. **场景切换 / 多 run 浏览**：未来场景多了之后

---

## 启动方式

```bash
python -m observation_tools \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --port 28391
```

浏览器打开 `http://127.0.0.1:28391`，默认选最末 -1 的 turn（避开末位 off-by-one）。
