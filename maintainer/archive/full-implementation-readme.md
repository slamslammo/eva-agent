# EVA-agent v0.5 完整实现方案

这组文档用于从零开始整理 **EVA-agent 的 v0.5 完整实现方案**。

它的目标不是描述当前仓库已经实现到哪里，也不是承接 phase 进展，而是先在 **严格对齐 EVA v0.5 术语与结构** 的前提下，给出一份完整、连贯、可逐章确认的实现文稿骨架。

## 为什么采用 sections 分章，而不是先写成长文

当前采用：
- 一份总目录文档
- 一组按章节拆开的 `sections/*.md`

原因：
1. 便于逐章确认后再扩写正文
2. 便于严格控制术语，不被局部上下文带偏
3. 便于处理章节之间的承上启下
4. 后续如需要再汇总成长文，可以从这些 section 自动或手工拼接

因此，当前推荐写作方式是：
- 先确认总目录与章节职责
- 再逐章确认
- 再写入每章正文

## 当前目录结构

- `eva-agent-full-implementation.md`
  - 主目录与章节摘要入口
- `sections/00-abstract.md`
- `sections/01-engineering-goals-and-invariants.md`
- `sections/02-overall-architecture.md`
- `sections/03-anchor-system.md`
- `sections/04-infrastructure-kernel.md`
- `sections/05-l1-homeostatic-sensing.md`
- `sections/06-l2-drive-layer.md`
- `sections/07-l3-adaptive-deliberation.md`
- `sections/08-l4-self-model-interfaces.md`
- `sections/09-l5-social-layer-boundaries.md`
- `sections/10-runtime-artifacts-and-state-objects.md`
- `sections/11-runtime-closed-loop.md`
- `sections/12-validation-and-invariant-tests.md`
- `sections/13-deployment-and-implementation-shape.md`
- `sections/14-conclusion.md`

## 当前写作约束

- 以 EVA v0.5 理论为术语基准
- 不因为参考材料中的命名而新造概念
- 当前先放下与 repo 已实现状态的融合
- 当前先把“完整实现方案”写清楚，再反过来映射当前工程
- 每一章在正式扩写正文前，先单独确认章节结构与写作边界
