# CLAUDE.md

## 项目定位
`eva-agent/` 是一个 **EVA v0.5 对齐**的 existence-centered agent 架构实验项目。

它的目标不是先做一个功能完善的 task-centered agent，而是先建立符合 EVA 的结构主干：kernel、L1 sensing、L2 drive、L3 deliberation、anchor 与 memory 的正确边界，再让后续能力在这条结构主干上生长。

## 当前主线
当前后续工作统一遵循：
- `docs/architecture.md`
- `docs/development/roadmap.md`
- 当前激活 phase 对应的 `docs/development/phase-*-plan.md` 与 `phase-*-progress.md`

当前仓库状态应理解为：
1. 已形成 **kernel baseline**：heartbeat-first、`tick / turn`、`instance_valid`、状态持久化、distress / yield
2. 已形成 **early L1 + L2-lite baseline**：external sensing、judgment、pressure 视图、history、patrol cadence
3. 已存在过渡性的 minimal action path，但它已冻结扩展，不再作为未来主路线

当前工作顺序：
1. 先完成总方案、roadmap 与当前 phase 文档统一
2. 再整理当前 phase implementation contract
3. 最后才进入对应 phase 的实施

## 当前已确认的原则
1. `eva-agent` 的公开表达与开发路线以 EVA v0.5 理论为先验起点，而不是从早期实现历史反推
2. heartbeat 是生命节律，不等于任务处理
3. `tick` 与 `turn` 必须分离
4. 外部信号、时间信号、内源信号都在同一主循环内处理，但 heartbeat deadline 不能被 ordinary work 长期阻塞
5. drive 是 contextual broadcast，不是 command
6. anchors 是 pre-generative structural constraints，不是 post-hoc filter
7. action release 必须独立于 reasoning，并保持 default inhibition
8. 旧文档可作为 baseline / historical / maintainer reference，但不能继续充当公开主线

## 工作原则
- docs-first，先固化项目定义、总纲与阶段合同，再进入实现
- 每次讨论形成的关键判断，要尽快写回项目文档，避免下次重复讨论
- 优先保证概念边界清晰、可解释、可持续迭代
- 不要提前跳到复杂工具、经济系统或高层成长机制实现，除非当前 architecture / roadmap / phase 文档已明确进入对应阶段
- 后续开发中的 Python 代码质量、可读性、风格一致性与变更纪律，统一遵循维护者内部规范，不再作为公开文档主线暴露

## 文档更新要求
当前阶段至少维护：
1. `README.md`、`docs/architecture.md` 与 `docs/development/` 之间的一致性
2. 公开主线与维护者参考材料的边界清晰
3. 当前激活 phase 的计划文档与进展文档同步更新

## 边界
- 持续执行、实现和文档沉淀都在 `eva-agent/` 项目目录内推进
- `chat/` 只保留 portfolio 层摘要与关键判断
