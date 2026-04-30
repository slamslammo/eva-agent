# 0. 摘要

## 0.1 从 EVA theory v0.5 到 EVA-agent

EVA-agent 的理论起点是 [EVA theory v0.5](https://github.com/slamslammo/eva-theory/blob/main/THEORY/v0.5-integrated.md)。v0.5 的核心主张，不是把 agent 继续写成 task executor，而是把 **continuous existence** 立为第一约束：主体必须先有自己的生命节律、内部 drive、候选生成边界、释放边界、记忆与学习闭环，然后任务处理才在这些边界之内发生。

因此，从 EVA theory 到 EVA-agent，不是把理论“翻译成一组功能模块”，而是把理论中的结构要求正式落成工程边界：heartbeat-first、instance validity、drive as internal context、anchor as pre-generative restriction、reasoning ≠ release、audit / memory / learning 分层，以及 outcome 回流后的 RPE / habit 闭环，都必须由代码结构承接，而不是停留在 prompt 或策略层。

## 0.2 EVA-agent 是什么

EVA-agent 不是一个以任务完成为中心的通用 agent 编排器，而是一个以 **continuous existence** 为第一约束的工程化主体架构。它回答的问题不是“如何让 agent 做更多事”，而是“如何让一个 agent 先以稳定、受约束、可持续的方式存在，再在这个前提下生长出感知、驱动、思辨、记忆与行动能力”。

从结构上看，EVA-agent 由 **五层主体结构 + 横跨层的 Anchor System + 基础设施层** 组成：
- 基础设施层提供 lifecycle kernel、instance identity、persistence 与 event bus；
- L1 负责 homeostatic sensing；
- L2 负责 drive；
- L3 负责 adaptive deliberation、memory、mediated release 与 learning；
- L4 与 L5 保留 self-model 与 social layer 的接口位置。

## 0.3 本文回答什么问题

本文的目标，不是总结当前仓库实现进展，而是说明：如果以 EVA v0.5 为理论起点，一个完整的 EVA-agent 应当如何被工程化落地。

全文围绕四个问题展开：

1. EVA-agent 的工程目标与不变量是什么；
2. 五层结构、Anchor System 与基础设施层如何分工；
3. sensing、drive、deliberation、release、memory、learning 如何接成持续运行闭环；
4. 这样的系统应如何验证，并以怎样的部署形态长期在线运行。

它与传统 task agent 的根本差异在于：EVA-agent 先建立主体结构与连续性边界，再允许能力在其上增长；而不是先追求功能面，再回头补边界。下一章将先给出这套完整实现方案的工程目标与不变量。