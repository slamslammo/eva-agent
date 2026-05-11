# 开发路线图

本文档说明 `eva-agent` 在 EVA v0.5 对齐后的**开发落地路线**。

它只回答两件事：
- **按什么顺序推进**
- **当前停在哪个 gate**

本文档不承担完整目标架构定义；相关文档分工如下：
- `docs/eva-agent-full-implementation.md`：英文公开完整 v0.5 目标架构
- `docs/current-status.md`：英文公开当前实现状态摘要
- `maintainer/development/development-standards.md`：本地开发规范
- `maintainer/development/module-organization-contract.md`：本地 canonical module organization
- `maintainer/development/codebase-realignment-plan.md`：本地代码级重组计划
- `maintainer/development/roadmap.md`：本地完整 v0.5 开发落地方案
- `maintainer/development/*-progress.md`：本地当前落地进展

## 1. 当前阶段判断

当前仓库已经具备：
- kernel baseline
- 已落地的 L1 / L2 baseline
- bounded reflex / routing / sensor-registry / drive-policy surfaces
- 稳定的 L3 deliberation / learning / mediator boundary
- 真实但 advisory-only 的 Anthropic-backed working-memory path，带 local fallback 与独立 LLM advisory audit

当前判断：**Phase C 已完成并完成 closeout；Stage D（reflex fast path、sensor registry composition、drive update semantics）已完成；Stage E working-memory Anthropic advisory integration 也已完成。Stage F 已进入 long-running infrastructure 入口，且 append-only size-management baseline 与 restart-matrix hardening 已完成首轮收口：kernel persistence seam 已具备 rotation / archive contract、segment-aware logical-history reads，以及 mixed-track + preexisting-archive restart coverage；当前仍保持 advisory-only / mediated-release 边界，不进入 24h soak 或 L4 contract。全量回归当前为 `243 tests` 通过。后续开发应继续以 `development-standards.md`、`module-organization-contract.md` 与 `codebase-realignment-plan.md` 作为 maintainer source of truth，并在不触碰 release authority 的前提下推进更强的 endurance / restart 组合验证。**

本轮 gate 已完成并完成落账，核心是把以下四层链条重新梳理并对齐：

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
| Phase C-4 baseline | working-memory adapter seam / protocol baseline | baseline 已形成，后续已在 Stage E 收口为真实但 advisory-only 的 Anthropic-backed path | `maintainer/development/phase-c-progress.md`、`maintainer/development/current-intake.md`、`docs/current-status.md` | 继续深化 retrieval / context composition，而不放松 authority boundary |
| Alignment / Consolidation Gate | 统一 theory → engineering → plan → progress | 已完成 | `maintainer/development/module-organization-plan.md`、`docs/current-status.md`、`maintainer/development/phase-c-progress.md` | 基于当前 stable owner tree 重新评估下一开发 slice |
| B-1 anchor residue closeout | 收紧 A-2 已落地的 pre-generative anchor restriction，并把 runtime gate projection 前移到 `ActionDomain` candidate materialization；将 `apply_structural_anchors(...)` 收窄为 residual compatibility projection seam | 已完成 | `maintainer/development/current-intake.md`、`maintainer/development/phase-c-progress.md`、`docs/current-status.md` | 进入 B-2 richer episodic retrieval |
| B-2 richer episodic retrieval | 深化 episodic retrieval / working-memory 读侧语义，让 retrieval 按 `situation_key`、`pressure_reason`、continuous `salience` 与 `drive_state_at_encoding` 组合排序，并保留 advisory-only 边界 | 已完成 | `maintainer/development/phase-c-progress.md`、`docs/current-status.md` | 进入 B-3 compatibility bridge demotion |
| B-3 compatibility bridge demotion | 继续压薄 `compatibility.py`，把通用 response selection / execution closeout / summary assembly 下放到 canonical `tool_edge/` owners | 已完成 | `maintainer/development/phase-c-progress.md`、`docs/current-status.md` | 进入 B-4 drive-native L3 shaping |
| B-4 drive-native L3 shaping | 继续把 reasoning / selection 从 pressure-led 微调推向 drive-native shaping，让 pressure 留在 projection / fallback 语义 | 已完成 | `maintainer/development/phase-c-progress.md`、`docs/current-status.md` | 进入 B-5 candidate / release vocabulary widening |
| B-5 candidate / release vocabulary widening | 在保持 mediator-owned default inhibition、anchor pre-generation 与 bounded tool-edge 的前提下，受限扩展 internal candidate profile / release-policy vocabulary | 已完成 | `maintainer/development/phase-c-progress.md`、`docs/current-status.md` | 评估下一项 mediated action-surface slice |
| Stage G（planned） | 清理 Phase A residuals，并落地 v0.6 capability landing（outcome vector / skill-source split / persistence hierarchy / stability metrics / Linux scenario alignment audit） | 规划中，尚未启动 | `maintainer/development/phase-a-residuals.md`、`maintainer/development/stage-g-v0.6-capability-landing-startup-instruction.md` | 先完成 G-0 residual clearance intake |

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
| L3 working-memory adapter | advisory-only adapter seam / protocol / real model-backed client shell / degraded fallback / separate audit track | 已形成真实但有界的 advisory path | `maintainer/development/phase-c-progress.md`、`maintainer/development/current-intake.md`、`docs/current-status.md` |
| Anchor / mediated release | 结构性候选约束与 default inhibition release boundary | 已有最小边界，尚非完整系统 | `maintainer/development/phase-b-progress.md` |
| Cognitive memory | salience retrieval / richer episodic memory / full skill library | 尚未完整落地 | `docs/current-status.md`、`maintainer/development/phase-c-progress.md` |
| L4 Self Model | 更高阶主体自我模型 | 未展开 | `docs/eva-agent-full-implementation.md` |
| L5 Social / External Coordination | 外部协同 / deployment 相关高层结构 | 未展开 | `docs/eva-agent-full-implementation.md` |

## 4. Alignment / Consolidation Gate

在继续推进 C-4 或更后续能力之前，当前这轮文档性 gate 已完成：

### 目标
- 把目标架构与当前进展正式拆开
- 把 theory 到 engineering 的关键过渡补齐
- 把开发路线与当前落地状态重新对齐
- 形成一套后续可直接承接开发的主线文档，而不是继续依赖聊天上下文

### 当前已成立
- `docs/eva-agent-full-implementation.md` 成为纯目标架构文档
- `docs/current-status.md` 成为英文公开当前状态文档
- `maintainer/development/development-standards.md` 成为本地开发规范来源
- `maintainer/development/module-organization-contract.md` 成为本地 canonical owner map 来源
- `maintainer/development/codebase-realignment-plan.md` 成为代码级重组分期来源
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
- **C-4 baseline**：working-memory adapter seam / protocol baseline（已形成，并已在后续 Stage E 扩展为真实但 advisory-only 的 Anthropic-backed path）

### 当前边界
- learning 只能在现有 mediator / compatibility bridge 边界内回流为 bounded bias
- habit path 只能缩窄或优先候选，不能绕过 runtime gate、anchors、mediator
- LLM 只能作为 working-memory / reasoning adapter，不是 release authority
- 即使 Stage E 已落地真实模型接入，working-memory 仍保留 degraded fallback、schema-bound normalization 与 advisory-only 语义

## 9. Phase D：L4 雏形

L4 只有在下层已经积累出足够稳定的行为史、memory 史与 release 史之后才有意义。

当前不提前展开实现细节，也不在 alignment gate 之前推进。

## 10. Stage G planning note

当前 maintainer 规划中，另有一条 **Stage G** 轨道，用于承接：
- Phase A closeout review 中识别出的 residual cleanup
- v0.6 capability landing 的后续结构落地

需要强调：
- Stage G 的历史起点来自 **Phase A A-1 ~ A-8 完整 review**
- 但它**不是**对历史 `Phase B` 的重命名，也**不是**对已完成 `Phase B / Phase C` 的回滚
- 历史 `Phase A / Phase B / Phase C` 与后续 `Stage D / E / F` 文档保持原样保留
- Stage G 的 maintainer source of truth 是：
  - `maintainer/development/phase-a-residuals.md`
  - `maintainer/development/stage-g-v0.6-capability-landing-startup-instruction.md`

## 11. 推进原则

- 先对齐架构与合同，再进入后续代码实现
- 先把结构搭对，再扩高层能力
- 过渡结构可以短期保留，但不再作为未来主路线继续长大
- 当前文档性 alignment gate、Stage D 与 Stage E 已完成；下一步在 stable owner tree 上重新评估 retrieval/context deepening 与后续 lower-layer capability slice
- 每个 phase 都应维持：目标、边界、进展三类文档的一致性

## 12. 相关文档

- `docs/eva-agent-full-implementation.md`
- `docs/current-status.md`
- `maintainer/development/development-standards.md`
- `maintainer/development/module-organization-contract.md`
- `maintainer/development/codebase-realignment-plan.md`
- `maintainer/development/phase-a-plan.md`
- `maintainer/development/phase-a-progress.md`
- `maintainer/development/phase-b-plan.md`
- `maintainer/development/phase-b-progress.md`
- `maintainer/development/phase-c-plan.md`
- `maintainer/development/phase-c-progress.md`
