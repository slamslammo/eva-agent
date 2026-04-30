# 3. 横跨层约束：Anchor System

## 3.1 Anchor 的位置

在 EVA-agent 里，Anchor System 不是第六层，也不是某个后置 safety filter。它回答的问题不是“已经生成的候选要不要拦”，而是：**当前系统究竟允许自己看见怎样的候选域。**

因此，Anchor 的职责是把约束前移到 candidate generation 之前：
- 它不拥有像 L1 / L2 / L3 那样的主状态；
- 它在生成前收缩 action domain；
- 它与 mediator 分工不同：Anchor 决定“什么能被生成”，mediator 决定“什么能被释放”。

![Anchor System overview](../../../docs/assets/architecture/anchor_system_overview.svg)

## 3.2 structural anchors 与 dynamic anchors

Anchor 由两类约束组成。

**structural anchors** 是稳定的硬边界，来自主体连续性、deployment capability、side effect class、execution boundary 与 integrity constraints。它们先于具体 deliberation 存在，决定哪些域原则上就不应开放。

**dynamic anchors** 则在 structural envelope 内根据当前状态进一步收缩可见域。它们的来源包括 runtime gate、instance validity、L1 threat / status signals、最近 outcome，以及 bounded learning 回流。dynamic anchors 可以收紧或重排当前可见域，但不能扩权到 structural anchors 之外。

## 3.3 capability restriction 与 parameter-domain restriction

Anchor 的正式作用至少有两类。

第一类是 **capability restriction**：决定哪些行动能力根本不进入候选空间。tool registry 里的潜在能力集合，不等于当前可生成能力集合。

第二类是 **parameter-domain restriction**：即使某个 capability 被允许，其目标范围、强度范围、速率范围、作用范围也仍需先被收缩。candidate generation 面对的不是“能力名 + 无限参数空间”，而是**已经带边界的 action schema**。

## 3.4 `G(s) -> A'(s) ⊆ A(s)` 的工程含义

Anchor 的形式化表达是：

```text
G(s) -> A'(s) ⊆ A(s)
```

这里最关键的不是公式本身，而是位置关系：`A'(s)` 不是生成后的残留物，而是**生成开始时唯一可见的域**。

它直接带来四个工程要求：

1. candidate generator 只能读取 restricted domain；
2. tool registry 描述潜在能力，不等于当前生成域；
3. mediator 负责 release，不替代 Anchor 的生成域收缩；
4. 末端 validator 可以存在，但只能是 defense-in-depth。

## 3.5 Anchor 与 kernel / L1 / L2 / L3 的关系

Anchor 不是悬空存在的，它与前几层有明确分工：

- **与 kernel**：kernel 决定主体此刻是否还能合法运行；Anchor 决定在合法运行前提下能看见怎样的候选域。
- **与 L1**：L1 回答“现在发生了什么”；Anchor 回答“在这些状态下什么仍允许被生成”。
- **与 L2**：drive 改变倾向与排序；Anchor 决定结构允许域。高强度 drive 不能放宽 Anchor。
- **与 L3**：reasoning、memory retrieval、candidate shaping 都必须在 `A'(s)` 中展开，而不是先在完整域里思考再后置删减。

因此，Anchor 真正把“约束先于生成”落成了工程结构。

下一章将进入基础设施层。