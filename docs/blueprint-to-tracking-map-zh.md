# Blueprint to Tracking Map

> 蓝图承诺 → 跟踪条目映射表：把 `architecture-implementation-blueprint-v0.6.md` 中的目标态承诺映射到 `implementation-tracking.md` 中的当前实现状态。

它回答的问题是：**对于每一条 blueprint 承诺，它对应哪一条 tracking 条目，现在的实现状态是什么？**

---

| Blueprint 承诺 | Tracking 条目 | 当前状态 | 缺口 / 说明 |
|---|---|---|---|
| 以 active persistence 方式理解 continuous existence | 暂无单独命名条目 | partial | 目前通过 rate-aware sensing、persistence hierarchy、多维 outcome 与 bounded exploration 组合体现，但 tracking 中还没有一个独立命名的“active persistence”条目。 |
| Heartbeat-first lifecycle | 1.1 `Bounded heartbeat / tick / turn runtime loop` | landed | — |
| Instance legitimacy | 1.1 `Instance legitimacy (lock / generation / lease)` | landed | — |
| Atomic current state 与 append-only history 分离 | 1.1 `Separated atomic current-state persistence and append-only audit substrate` | landed | — |
| Framework / scenario activation boundary | 1.1 `Explicit scenario activation through RuntimeScenarioBundle` | landed | — |
| Runner-owned startup assembly | 1.1 `Runner-owned startup assembly for shipped scenarios` | landed | — |
| Fast/slow 双路闭环运行时组合 | 1.1 `Integrated fast/slow closed-loop runtime composition` | landed | — |
| Persistence-target registration surface | 1.1 `Explicit persistence hierarchy contract` | landed | — |
| Persistence Levels 5–7 | 1.1 `Persistence target Levels 5–7` | deferred | 理论预留；机制未实现。 |
| Observable stability 测量表面 | 1.1 `Architecture-neutral stability profile calculation from trace files` | landed | — |
| Comparative stability hypothesis 评估程序 | 1.1 `Comparative Stability Hypothesis evaluation program` | deferred | metric surface 已有；比较实验程序尚未落地。 |
| Sensor registry 与 normalized sensing contract | 1.2 `Normalized sensor registry and sensing contract` | landed | — |
| 带 rate metadata 的 scenario-declared dimension spec | 1.2 `Scenario-declared dimension specifications with rate-sensing tier metadata` | landed | — |
| 带显式 unknown fallback 的 state + rate sensing | 1.2 `Rate-aware sensing with explicit unknown fallback` | landed | — |
| 带 threat/status 分类的 signal publication | 1.2 `Signal publication with explicit status / threat classification` | landed | background routing 在 tracking 中是隐含的，而不是单独一行。 |
| Drive preset 与 drive-update seam | 1.3 `Drive preset and drive-update seam` | landed | update seam 明确；decay/recovery 没拆成独立 tracking 行。 |
| L2 持有所有权的 read-only drive broadcast | 1.3 `Read-only drive broadcast with L2-owned state authority` | landed | — |
| 带 urgency modulation 的 pressure projection | 1.3 `Pressure projection with urgency modulation and bounded anticipatory pressure` | landed | — |
| Protective reflex fast path | 1.3 `Protective reflex fast path parallel to slower deliberation` | landed | — |
| Deliberation input contract | 1.4 `Canonical deliberation input contract` | landed | — |
| 四层记忆表面 | 1.4 `Four-layer memory surface (working / episodic / semantic / procedural)` | partial | semantic indexing/windowing 和 dedicated procedural store 仍未完成。 |
| Mediator 作为独立 peer circuit | 1.4 `Mediator as independent peer circuit (default inhibition + selective release)` | landed | — |
| Runtime-only release token boundary | 1.4 `Runtime-only release token boundary` | landed | — |
| 带 learned overlay 的 drive-weighted candidate assessment | 1.4 `Drive-weighted candidate assessment with bounded learned overlays` | landed | — |
| 规范多维 outcome 支持 | 1.4 `Append-only learning outcome records with canonical OutcomeVector support` | landed | — |
| RPE 作为内部更新信号 | 1.4 `RPE-like learning as internal update signal` | landed | tracking 用的是 “RPE-like” 表述；blueprint 对 vector semantics 更严格。 |
| Habit shaping 与 skill crystallization | 1.4 `Habit shaping and skill crystallization through habit track` | landed | — |
| Advisory-only working-memory assembly | 1.4 `Advisory-only working-memory assembly` | landed | — |
| Model-backed working-memory advisory path | 1.4 `Model-backed working-memory advisory path with bounded fallback` | landed | — |
| 基于 append-only artifact 的 episodic retrieval | 1.4 `Episodic retrieval over append-only artifacts` | landed | — |
| Semantic memory 作为 first-class storage 且有界参与 L3 | 1.4 `Semantic memory — first-class storage + exact query + bounded L3 participation` | partial | store-side windowing / indexing 尚未实现。 |
| Semantic memory → L2 安全路径 | 1.4 `Semantic memory → L2 drive-weight semantics` | deferred | 安全路径保留但未实现。 |
| 基于 habit-backed substrate 的 procedural memory | 1.4 `Procedural memory via existing habit-track substrate` | partial | 显式 surface 已有，但不是 dedicated procedural store。 |
| Working-memory 接口复审阈值 | 1.4 `Working-memory interface signature` | partial | 接口参数仍在累积。 |
| Anchor 生成前限制 | 1.5 `Framework-owned action domain and pre-generative restriction surface` | landed | — |
| Scenario-owned anchor admission policy | 1.5 `Scenario-owned anchor admission policy through active bundle seam` | landed | — |
| Capability restriction 与 parameter-domain restriction | 1.5 `Capability restriction and parameter-domain restriction inside the active action domain` | landed | — |
| Mediated candidate filtering / selection / execution | 1.5 `Mediated candidate filtering, selection, and execution path` | landed | — |
| Anchor 三向区分 | 1.5 `Anchor three-layer distinction (mechanism / constitutional policies / emergent overlays)` | partial | emergent overlay 一侧仍比理论框架更窄。 |
| Same-scenario inherited-prior distillation pipeline | 1.6 `Same-scenario inherited-prior distillation pipeline` | landed | — |
| Same-scenario inherited-prior loading and bounded participation | 1.6 `Same-scenario inherited-prior loading and bounded deliberation participation` | landed | — |
| 带 provenance 的 capability-tracking skill registry | 1.6 `Capability provenance-carrying skill registries` | partial | provenance 已显式，但更广的 theory-side source taxonomy 尚未作为独立 runtime source 激活。 |
| Cross-scenario inherited-prior transmission | 1.6 `Cross-scenario inherited-prior transmission` | deferred | 明确延期。 |
| Exploration as growth driver | 1.7 `Exploration as growth driver` | deferred | blueprint 已承诺；runtime mechanism 尚未启动。 |
| L4 self-model runtime | 1.7 `L4 self-model runtime` | deferred | 仅预留。 |
| L5 social-layer runtime | 1.7 `L5 social-layer runtime` | deferred | 仅预留。 |
| Generic scenario loader / validator | 1.7 `Generic scenario loader / validator` | deferred | 当前仍是显式 runner 装配。 |
| Multi-scenario runtime switching | 1.7 `Multi-scenario runtime switching inside one process` | deferred | 明确不在当前范围。 |
| 六表面场景契约 | 2 `RuntimeScenarioBundle`、`SensorPolicyBundle`、`ActionPolicyBundle`、`AnchorPolicyBundle`、`OutcomeObserverBundle`、`PriorSkillBundle` | partial | 五个 surface 为 production；`PriorSkillBundle` 因 provenance-boundary deepening 仍为 partial。 |
| 场景所有 persistence 注册 | 2 `Scenario-owned persistence hierarchy registration` | landed | — |
| 契约层的规范多维 outcome | 2 `Canonical multi-dimensional OutcomeVector` | landed | — |
| 带 scenario-owned provenance 输入的 framework-owned skill registry | 2 `Framework-owned skill registries with scenario-owned provenance inputs` | landed | — |
