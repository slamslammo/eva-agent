# EVA-Agent

**EVA v0.5 对齐的 existence-centered agent 架构实验项目。**

EVA-agent 不是从"任务优先的 agent + 逐步增加编排"开始，而是从结构性问题开始：agent 如何保持同一个运行主体、drive 如何作为上下文塑造行为、candidate 生成如何在 release 之前被约束、memory 和 learning 如何保持在明确的边界内。

本架构以 [EVA theory v0.5](https://github.com/slamslammo/eva-theory) 及其 v0.6 扩展为理论基础。理论文档包含完整的动机和推导；本仓库展示当前落地了什么、如何落地。

## 当前状态

仓库当前呈现为"框架 + 场景"分离的 EVA runtime，包含一个主参考运行时和一个 bounded 验证运行时。

- **Linux runtime** — 主参考运行时，已稳定交付
- **Crafter** — bounded 端到端 second scenario，用于验证跨场景框架接口的完整性
- **近期里程碑**：Stage I 工程收尾，对应 EVA v0.6 unified release。框架/场景边界现已稳定。

当前优先工作：在不削弱 advisory-only 和 mediator-owned release 边界的前提下，深化 memory 组合能力、扩展 mediated action 词汇表。

## 从哪开始

根据你的需求选择入口：

**想快速了解整体架构**
→ [`docs/architecture-overview.md`](docs/architecture-overview.md)（英文）

**想了解框架落地了什么**
→ [`docs/eva-framework-implementation.md`](docs/eva-framework-implementation.md)（英文）

**想了解场景如何接入框架**
→ [`docs/scenarios-SPEC.md`](docs/scenarios-SPEC.md)（英文）
→ 具体场景文档：[`scenarios/linux_runtime/SPEC.md`](scenarios/linux_runtime/SPEC.md)、[`scenarios/crafter/SPEC.md`](scenarios/crafter/SPEC.md)

**想查理论承诺的落地状态**
→ [`docs/implementation-tracking.md`](docs/implementation-tracking.md)（英文）

**想读理论**
→ [eva-theory 仓库](https://github.com/slamslammo/eva-theory)（英文）

## 仓库结构

```
eva-agent/
├── README.md                   ← 英文入口（本文件）
├── README-zh.md                ← 中文入口
│
├── docs/                       ← 公开英文文档
│   ├── architecture-overview.md          ← 架构鸟瞰
│   ├── eva-framework-implementation.md   ← 框架当前落地了什么
│   ├── scenarios-SPEC.md               ← 跨场景接入契约
│   ├── implementation-tracking.md       ← 理论承诺 → 落地状态跟踪
│   └── archive/                        ← 历史参考材料
│
├── eva/                       ← Python 框架实现
├── scenarios/                  ← 场景包（每个含自己的 SPEC.md）
│   ├── linux_runtime/
│   └── crafter/
├── runners/                    ← 每个场景的显式启动路径
├── tests/
├── stability_metrics/           ← 架构无关的稳定性测量工具
├── inheritance_distillation/    ← 同场 prior 蒸馏 pipeline
└── maintainer/                 ← 内部工程记录（非公开）
```

## 核心架构承诺

以下是 EVA-agent 实现的核心结构属性，不是建议：

- 持续存在作为第一序约束
- heartbeat-first 运行时结构，bounded `tick` / `turn` 分离
- drive 作为上下文广播，而非指令
- anchors 作为生成前结构约束（`G(s) → A'(s) ⊆ A(s)`）
- reasoning 在结构上独立于 release；mediator 拥有 action release 权限
- default inhibition：静息状态为 inaction
- 分离的 audit、memory、learning track
- 框架/场景边界：框架拥有运行时权威和结构不变量；场景拥有世界特定内容

## 相关项目

- **[eva-theory](https://github.com/slamslammo/eva-theory)**：权威理论、术语、设计文档。英文。

## License

CC BY 4.0