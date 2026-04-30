# 开发路线图

本文档说明 `eva-agent` 在 EVA v0.5 对齐后的**开发落地路线**。

它只回答两件事：
- **按什么顺序推进**
- **当前停在哪个 gate**

本文档不承担完整目标架构定义；相关文档分工如下：
- `docs/eva-agent-full-implementation.md`：英文公开完整 v0.5 目标架构
- `docs/current-status.md`：英文公开当前实现状态摘要
- `maintainer/development/roadmap.md`：本地完整 v0.5 开发落地方案
- `maintainer/development/*-progress.md`：本地当前落地进展

## 1. 当前阶段判断

当前仓库已经具备：
- kernel baseline
- 已落地的 L1 / L2 baseline
- compatibility projection / compatibility execution path
- Phase B 最小 L3 骨架
- Phase C 的 C-1 / C-2 / C-3 首轮落地，以及 C-4 protocol / placeholder baseline

当前判断：**Phase C 的 C-1 / C-2 / C-3 已完成，C-4 baseline 已形成，但继续向前开发暂时挂起；当前优先进入一次完整的 alignment / consolidation gate。**

这个 gate 的目标不是继续堆功能，而是先把以下四层链条彻底梳理清楚并对齐：

1. 完整 v0.5 理论架构
2. 完整 v0.5 工程架构
3. 完整 v0.5 开发落地方案
4. eva-agent 当前落地进展

## 2. 当前总进展表

| 阶段 | 目标 | 当前状态 | 主要证据 | 下一 gate |
| --- | --- | --- | --- | --- |
| Phase A | 建立 L1 / L2 主干与最小广播通路 | 已完成主干落地 | `maintainer/development/phase-a-progress.md` | 维持 closeout 口径一致 |
| B0 | 冻结 L3 稳定上游输入面 | 已冻结 | `maintainer/development/phase-a-progress.md`、`docs/eva-agent-full-implementation.md` | 继续作为 L3 输入合同 |
| Phase B | 建立 L3 最小骨架与 release 边界 | 已完成评审后收口 | `maintainer/development/phase-b-progress.md` | 作为 Phase C 学习层底座 |
| Phase C-1 | 最小 learning slice | 已完成 | `maintainer/development/phase-c-progress.md` | 进入 C-2 |
| Phase C-2 | learning reinforcement | 已完成 | `maintainer/development/phase-c-progress.md` | 进入 C-3 |
| Phase C-3 | habit crystallization closeout | 已完成 | `maintainer/development/phase-c-progress.md` | 进入 alignment gate |
| Phase C-4 baseline | working-memory adapter seam / protocol baseline | 已形成 baseline，未继续扩展 | `maintainer/development/phase-c-progress.md` | 等待 alignment 完成后再决定继续推进 |
| Alignment / Consolidation Gate | 统一 theory → engineering → plan → progress | 当前进行中 | 本轮文档重构 | 重新评估 C-4 与后续开发 |

## 3. 当前 v0.5 落地视图

除了 phase 视角，当前还可以从结构视角理解仓库已经落到哪里：

| 结构条目 | 目标角色 | 当前落地状态 | 主要证据 |
| --- | --- | --- | --- |
| Infrastructure | kernel / identity / persistence / event baseline | 已形成稳定底盘 | `maintainer/development/phase-a-progress.md` |
| L1 Homeostatic Sensing | state + rate sensing / normalized signal input | baseline 已落地 | `maintainer/development/phase-a-progress.md` |
| L2 Drive Layer | continuous drive state / read-only drive broadcast / reflex seam | baseline 已落地 | `maintainer/development/phase-a-progress.md` |
| Compatibility projection layer | pressure / history / compatibility execution bridge | 仍保留，但已降级为 compatibility layer | `maintainer/development/phase-a-progress.md`、`maintainer/development/phase-b-progress.md` |
| L3 core skeleton | candidate / value judgment / mediator / audit / memory stub | 最小骨架已落地 | `maintainer/development/phase-b-progress.md` |
| L3 learning loop | outcome delta / bounded bias / habit crystallization | C-1 / C-2 / C-3 已完成 | `maintainer/development/phase-c-progress.md` |
| L3 working-memory adapter | advisory-only adapter seam / protocol / placeholder / client shell | baseline 已形成，后续扩展暂挂 | `maintainer/development/phase-c-progress.md` |
| Anchor / mediated release | 结构性候选约束与 default inhibition release boundary | 已有最小边界，尚非完整系统 | `maintainer/development/phase-b-progress.md` |
| Cognitive memory | salience retrieval / richer episodic memory / full skill library | 尚未完整落地 | `docs/current-status.md`、`maintainer/development/phase-c-progress.md` |
| L4 Self Model | 更高阶主体自我模型 | 未展开 | `docs/eva-agent-full-implementation.md` |
| L5 Social / External Coordination | 外部协同 / deployment 相关高层结构 | 未展开 | `docs/eva-agent-full-implementation.md` |

## 4. Alignment / Consolidation Gate

在继续推进 C-4 或更后续能力之前，当前先完成以下文档性 gate：

### 目标
- 把目标架构与当前进展正式拆开
- 把 theory 到 engineering 的关键过渡补齐
- 把开发路线与当前落地状态重新对齐
- 形成一套后续可直接承接开发的主线文档，而不是继续依赖聊天上下文

### 完成后应成立
- `docs/eva-agent-full-implementation.md` 成为纯目标架构文档
- `docs/current-status.md` 成为英文公开当前状态文档
- `maintainer/development/roadmap.md` 成为开发落地总路线
- `maintainer/development/phase-c-progress.md` 等 progress 文档成为当前事实来源
- `README.md` 只保留入口、摘要与阅读顺序

## 5. Phase A：L1 / L2 结构升级

### 目标
建立符合 EVA 的基础通路：

```text
sensing -> signal classification -> drive update -> drive broadcast
```

### 已成立边界
- state + rate sensing baseline
- 最小 signal publication
- continuous drive state
- read-only drive broadcast
- compatibility pressure view / response path 降级为兼容层

### 后续要求
- 不把 compatibility path 重新升格为主结构 owner
- 保持与公开目标架构文档和公开当前状态文档口径一致

## 6. B0：Phase B entry gate

### 目标
在进入 L3 功能推进前，冻结稳定可依赖的最小上游输入面。

### 已冻结输入
- `drive_broadcast`
- `signal_batch`
- `runtime_gate_context`

### 后续要求
- 这三条输入面继续作为 L3 的唯一强制上游合同
- working-memory 只能作为可选增强输入

## 7. Phase B：L3 最小骨架

### 目标
先建立 L3 的结构性边界，而不是先追求复杂 reasoning。

### 已成立边界
- candidate generation / value judgment / release 分离
- 最小 mediator
- structural anchor 边界
- audit / memory 双轨

### 后续要求
- reasoning 不得直连 side effect
- compatibility release 仍只经当前 mediator / bridge 边界进入下游

## 8. Phase C：学习能力

### 目标
在既有 L3 结构上引入 outcome-based adaptation，并逐步推进到 habit crystallization 与 llm-assisted working memory。

### 当前状态
- **C-1**：最小 learning slice（已完成）
- **C-2**：learning reinforcement（已完成）
- **C-3**：habit crystallization（closeout 已完成）
- **C-4 baseline**：working-memory adapter seam / protocol baseline（已形成）

### 当前边界
- learning 只能在现有 mediator / compatibility bridge 边界内回流为 bounded bias
- habit path 只能缩窄或优先候选，不能绕过 runtime gate、anchors、mediator
- LLM 只能作为 working-memory / reasoning adapter，不是 release authority
- 当前不在 alignment gate 完成前继续扩写 C-4

## 9. Phase D：L4 雏形

L4 只有在下层已经积累出足够稳定的行为史、memory 史与 release 史之后才有意义。

当前不提前展开实现细节，也不在 alignment gate 之前推进。

## 10. 推进原则

- 先对齐架构与合同，再进入后续代码实现
- 先把结构搭对，再扩高层能力
- 过渡结构可以短期保留，但不再作为未来主路线继续长大
- 当前先完成文档性 alignment gate，再决定 C-4 的进一步推进
- 每个 phase 都应维持：目标、边界、进展三类文档的一致性

## 11. 相关文档

- `docs/eva-agent-full-implementation.md`
- `docs/current-status.md`
- `maintainer/development/phase-a-plan.md`
- `maintainer/development/phase-a-progress.md`
- `maintainer/development/phase-b-plan.md`
- `maintainer/development/phase-b-progress.md`
- `maintainer/development/phase-c-plan.md`
- `maintainer/development/phase-c-progress.md`
