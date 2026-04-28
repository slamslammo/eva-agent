# 开发路线图

本文档说明 `eva-agent` 在 EVA v0.5 对齐后的分阶段开发路线。

它回答的是：**接下来按什么 phase 推进，以及当前处在哪个 phase。**

这份文档只保留公开层面的路线，不展开具体实现细节。

## 1. 当前阶段

当前仓库已经具备：
- kernel baseline
- 当前已落地的 L1 / L2 baseline（state + rate sensing、minimal signal publication、continuous drive state、read-only drive broadcast）
- compatibility pressure view / history / minimal action path

当前判断：**Phase A 主干已落地并完成 B0 输入冻结；Phase B 已进入 L3 最小骨架的首轮实现。**

因此，下一步重点不再是解释 B0，而是继续收紧 **Phase B：L3 最小骨架** 的合同、验证与表达边界，尤其是：
- `turn_completed.details.deliberation` 只暴露 `{ outcome, selected_action }`
- `turn_completed.details.response` 只暴露 `{ pressure_id, pressure_type, selected_action }`
- `response_selected` 只保留最小 downstream surface，完整执行细节回收到 append-only history / audit

## 2. Phase A：L1 / L2 结构升级（主干已落地，A5 closeout 进行中）

### 目标
建立一条符合 EVA 的基础通路：

```text
sensing -> signal classification -> drive update -> drive broadcast
```

### 重点
- 补齐 state + rate sensing
- 建立最小 signal publication contract
- 将 pressure 过渡视图升级为 continuous drive state
- 建立 read-only drive broadcast
- 保持当前最小 action path 只作为兼容层，不继续扩展

### 完成后应成立
- L1 不再只有当前态采样，也具备最小 rate sensing
- signal 已按 `threat / status / background` 统一发布，且 routing seam 的边界被明确说明
- drive state 为连续更新值
- L3 只能读取 drive broadcast，不能改写 drive

## 3. B0：Phase B entry gate（已冻结）

### 目标
在进入 Phase B 功能开发前，先冻结 L3 可稳定依赖的最小上游输入面。

### 必须成立
- `drive_broadcast` 成为 L2 -> L3 的 canonical read surface
- `signal_batch` 成为 L1 -> downstream 的最小标准化输入
- `runtime_gate_context` 成为 kernel -> downstream 的最小运行边界输入
- `active_pressures.json` 明确降级为 compatibility projection
- `response.py` 明确冻结为 pressure-led compatibility path

## 4. Phase B：L3 最小骨架（进行中）

### 目标
先建立 L3 的结构性核心，而不是先追求复杂推理。

### 重点
- 冻结核心合同
- 建立最小 mediator
- 建立 structural anchors
- 分离 candidate generation / value judgment / release
- 建立 cognitive memory 雏形

### 完成后应成立
- reasoning 无法直接触发 side effect
- 候选生成受 capability 与 parameter domain 双重限制
- audit trail 与 cognitive memory 双轨并存

## 5. Phase C：学习能力

### 目标
在既有 L3 结构上引入 outcome-based adaptation。

### 重点
- outcome delta
- RPE-like evaluation
- habit track / skill crystallization
- 可替换的 working-memory interface

### 完成后应成立
- 历史 outcome 能影响后续 candidate 释放倾向
- 部分常见情境能从 deliberative path 迁移到 habit track
- LLM 只能作为 working-memory / reasoning adapter，而不是 release authority

## 6. Phase D：L4 雏形

L4 只有在前面几层已经积累出足够多的行为史与 memory 史之后才有意义。

当前不提前展开实现细节。

## 7. 推进原则

- 先对齐架构与合同，再进入代码实现
- 先把结构搭对，再扩高层能力
- 过渡结构可以短期保留，但不再作为未来主路线继续长大
- 每个 phase 都应有明确的完成标准与进展记录

## 8. 相关文档

- `docs/architecture.md`
- `docs/development/phase-a-plan.md`
- `docs/development/phase-a-progress.md`
