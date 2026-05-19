# 场景契约规范

**状态**：Stage G capability landing 和 Stage H second-scenario 验证后的落地场景契约  
**范围**：`scenarios/` 下的场景包  
**配套文档**：`docs/eva-framework-implementation-zh.md`、`scenarios/linux_runtime/SPEC.md`、`scenarios/crafter/SPEC.md`

---

## 目的

本文档描述当前代码库实际使用的场景契约。场景提供 EVA 框架操作的具体世界特定内容。框架保留运行时权威和结构不变量；场景供给框架读取的内容。

当前仓库包含一个主 Linux runtime 场景和一个 bounded Crafter 验证场景。下面的契约以跨场景层级编写。

## 必需场景装配

场景包必须装配并导出一个与 `eva/scenario_bundle.py` 兼容的 runtime bundle。

当前 bundle 形状是 `RuntimeScenarioBundle`，包含：
- `drive_preset`
- `sensors`
- `actions`
- `anchors`
- `outcome_observers`
- `prior_skills`

场景可以通过辅助模块组织这些部分，但这六个 surface 是当前仓库的规范集成契约。

## 必需 bundle 组件

### 1. Drive preset

场景必须提供一个定义以下内容的 `DrivePreset`：
- drive 类型
- dimension-to-drive mapping
- default drive-update 策略输入
- 可选 curiosity drive 指定

框架拥有 drive state 更新和下游只读 broadcast。场景提供具体 drive 族。

### 2. Sensor policy bundle

场景必须提供返回有序 L1 sensor spec 的 sensor builders。

当前代码库中这包括：
- 具体 sensor-spec builders
- 框架 registry 使用的有序 sensor-provider 工厂
- 当 judgment / pressure projection 依赖场景塑造的 dimensions 时的场景所有 dimension specs

框架拥有 `SensorRegistry`、`SensingContext` 和归一化 `SensorOutput`。场景拥有被 sensing 的内容。

### 3. Action policy bundle

场景必须提供具体 response/action 策略，包括：
- action 名称
- action posture/state mapping
- candidate 构建
- candidate 过滤
- 最终 action 选择
- 具体 execution handler

框架拥有 mediated release 和 execution 结构。场景拥有具体 action 词汇表和 action 行为。

### 4. Anchor policy bundle

场景必须提供：
- candidate-profile 名称
- candidate schema 使用的 drive-impact defaults
- schema admission 逻辑
- restriction-reason 逻辑

框架拥有 `ActionDomain` 结构和结构性/dynamic anchor 处理。场景拥有具体场景 admission 策略。

### 5. Outcome observer bundle

场景必须提供：
- release outcome 的 expected-outcome label
- post-action outcome 评估
- learning-content payload 构建

框架拥有 learning-record 结构和 append-only 记录。场景拥有具体 action outcome 在该世界中意味着什么的语义。

### 6. Prior-skill bundle

场景必须提供：
- 当前 prior-skill 使用的情况匹配
- situation-key 构建
- habit-bias 摘要
- habit-skill 派生
- 将 learning outcome 的读侧映射回当前场景词汇表
- 可以参与带 provenance 元数据的框架 skill registry 的场景所有 prior record 或 prior-skill 策略

框架拥有 dataclass、skill registry 和 append-only learning track。场景拥有体验摘要和重用、及填充这些框架所有 registry surface 的场景本地 prior 内容的具体策略。

## 激活模型

一个 runtime 激活一个场景。

典型启动模式：
1. runner 导入选定的场景
2. runner 激活场景 bundle
3. runner 注册匹配的 persistence hierarchy
4. 如果场景需要 runner 所有者的 observations 或 env-backed state，runner 通过通用 runtime hook 将这些 fact 注入现有 sensing 接口
5. runner 调用 `eva.kernel.main.run_runtime()` 中的通用框架循环

当前仓库使用 `runners/run_linux.py` 和 `runners/run_crafter.py` 作为规范示例。

`eva/scenario_bundle.py` 要求先显式激活。没有场景被激活时没有静默 fallback，场景所有者的启动装配也负责注册匹配的 persistence hierarchy。

当场景需要 runner 所有者 observations（而非仅 filesystem sensing）时，框架仍拥有 cadence 和 patrol 执行；runner 仅通过现有 sensing 接口向其注入额外共享事实。

## 场景可以拥有什么

场景可以拥有：
- 具体 drive 族
- 具体 sensor dimension 和 payload 策略
- 具体 action 名称和 side effect
- 具体 candidate profile 和 anchor reason
- 具体 expected-outcome label
- 具体 prior-skill 和 habit 启发式
- 场景本地辅助模块和文档
- 向框架循环注入有界 observations 的场景本地 wrapper/runtime adapters

## 场景不得拥有什么

场景不得：
- mint release authority
- 绕过 mediator-owned execution
- 从更高层直接写入框架 drive state
- 重写 append-only audit、learning 或 history track
- 接管 kernel cadence、instance legitimacy 或 persistence 权威

即使场景提供了大部分 runtime 内容，这些仍为框架职责。

## 每场景文档

每个场景应在 `scenarios/<name>/SPEC.md` 中记录其具体内容。

该每场景规范应描述为那个世界 shipped 的实际 drive 集、sensor、action、anchor、outcome observer、prior-skill 策略和 runner/runtime 形态。

## 当前落地契约 surface

除原始 Phase A 装配接口外，当前仓库已将以下作为落地跨场景契约 surface：
- 通过 `eva/scenario_bundle.py` 的显式场景激活
- 与激活配对的场景所有者 persistence-hierarchy 注册
- 用于通用 judgment / pressure projection 的场景所有 dimension specs
- 当场景需要时，通过现有 sensing 接口注入 runner 所有者 shared-facts
- 通过 `eva/l3_deliberation/contracts.py::OutcomeVector` 的规范多维 outcome 记录
- 带场景所有者 provenance-bearing prior / habit 输入的框架所有 skill registry

这些不再是未来 placeholder；它们是当前框架/场景边界的一部分。

## 当前契约限制

当前契约在设计上仍小于更长期的 EVA 设计空间。

当前未提供：
- 通用场景 validator
- 独立场景 manifest 格式
- 多场景 runtime 切换

这些可以后续添加，但不在此处描述为已落地特性。
