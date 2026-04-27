# eva-agent

`eva-agent` 是一个 **EVA v0.5 对齐**的 existence-centered agent 架构实验工程。

它关注的不是如何把 agent 做成更强的 task orchestrator，而是如何先建立一条符合 EVA 的结构主干，使后续能力在正确的位置上生长：
- continuous existence as a first-order constraint
- drive as contextual broadcast
- anchors as pre-generative structural constraints
- action release structurally distinct from reasoning
- audit trail 与 cognitive memory 分层

## 当前状态

当前仓库应被理解为一个 **early reference implementation / partial instantiation**，还不是完整 EVA 系统。

目前已经成立的资产包括：
- kernel baseline：heartbeat-first、`tick / turn`、`instance_valid`、状态持久化、distress / yield
- Phase A 完成后的 L1 / L2 主干：state + rate sensing、Signal Bus、continuous drive state、read-only drive broadcast
- compatibility projection layer：pressure 视图、survival history、temporary minimal action path

当前状态应理解为：**Phase A 已完成，下一步进入 Phase B 规划与实施准备**。

## 阅读顺序

1. `docs/architecture.md`
   - 总方案、分层与关键合同
2. `docs/development/roadmap.md`
   - 分阶段路线
3. `docs/development/phase-a-plan.md`
   - 当前 Phase A 计划
4. `docs/development/phase-a-progress.md`
   - 当前 Phase A 进展
5. `docs/development/phase-a-implementation-contract.md`
   - 当前 Phase A 的实施合同

## 当前阶段不做

当前阶段不做：
- 扩当前 minimal action path 的动作谱系
- 把 pressure / viability-gap 视图当作长期核心控制模型
- 提前把 LLM 接成架构 prerequisite
- 提前进入完整 L4 / L5

## 仓库结构

- `eva/`：当前 Python 实现
- `tests/`：当前验证资产
- `docs/architecture.md`：公开总方案
- `docs/development/`：路线、计划、进展与实施合同
