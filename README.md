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
- 当前已落地的 L1 / L2 baseline：state + rate sensing、deterministic judgment、minimal signal publication、continuous drive state、read-only drive broadcast
- compatibility projection layer：pressure 视图、survival history、temporary minimal action path

当前状态应理解为：**Phase A 主干已落地，当前进入 A5 strict closeout / audit；B0 已冻结 L3 最小输入合同；Phase B 最小骨架已完成评审后收口；Phase C 已完成 C-1，C-2 learning reinforcement 已基本收口，C-3 habit crystallization closeout 已完成，当前进入 C-4 LLM working-memory adapter 的 protocol / placeholder baseline。**

## 当前 Phase C 重点

当前 Phase C 已不再只是规划启动，当前已形成的主线包括：
- **C-1 已完成**：`outcome delta`、`RPE-like evaluation`、post-hoc learning outcome、bounded bias 回流
- **C-2 已基本收口**：evidence / recency / stability / confidence gating 已进入 learning / working-memory 读侧
- **C-3 closeout 已完成**：crystallized habit skill、单一强 skill 的 bounded candidate narrowing、以及对应 observability / explainability 已成立
- **C-4 当前处于 baseline**：可替换 `working-memory interface`、`local_rule_based / auto / llm_assisted` backend seam、`inert / heuristic` placeholder、以及独立 model-client shell / config shell 已成立

当前 `active_pressures.json` 与 `response.py` 仍保留，但只作为 compatibility layer，不是未来 L3 的 owner。

## 阅读顺序

1. `docs/architecture.md`
   - 总方案、分层与关键合同
2. `docs/development/roadmap.md`
   - 分阶段路线
3. `docs/development/phase-c-plan.md`
   - 当前 Phase C 计划
4. `docs/development/phase-c-progress.md`
   - 当前 Phase C 进展
5. `docs/development/phase-b-plan.md`
   - Phase B 计划
6. `docs/development/phase-b-progress.md`
   - Phase B 进展
7. `docs/development/phase-a-plan.md`
   - 当前 Phase A 计划
8. `docs/development/phase-a-progress.md`
   - 当前 Phase A 进展
9. `docs/development/phase-a-implementation-contract.md`
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
