# Phase A Implementation Contract

本文档定义 **Phase A：L1 / L2 结构升级** 的实施合同。

Phase A 当前已经完成主干落地；本文保留为该阶段的模块级实施合同记录与边界基线，供后续回看 Phase A 当时冻结了哪些工程接缝。

它回答的是：**在不破坏当前 heartbeat-first baseline 的前提下，Phase A 应该改哪些模块、冻结哪些边界、通过什么验证推进。**

## 1. Phase A 范围

Phase A 只处理以下结构升级：
- state + rate sensing
- Signal Bus
- continuous drive state
- read-only drive broadcast

Phase A 不负责：
- 完整 mediator
- 完整 anchor system
- cognitive memory 正式落地
- LLM working-memory integration

## 2. 当前代码资产与处理方式

### 2.1 保留为稳定底盘

以下模块在 Phase A 中应尽量保持稳定，只做最小接缝修改：

- `eva/kernel/instance.py`
  - 保留单实例合法性与 generation / lease 机制
- `eva/lifecycle.py`
  - 保留 heartbeat-first、`tick / turn` 分离、turn guard window、critical / yield 语义
- `eva/kernel/state.py`
  - 保留 current-state 原子写入与 append-only log 模式
- `eva/kernel/config.py`
  - 保留 `EvaPaths` 与现有 runtime artifact 路径约定

### 2.2 优先复用的判断与投影层

以下模块优先复用其现有语义，再逐步重组：

- `eva/l1_sensing/judgment.py`
  - 当前 deterministic judgment 逻辑可继续作为 Phase A 的规则基线
- `eva/l2_drive/pressure.py`
  - 当前 pressure id、opened / resolved transition 逻辑可暂时保留为兼容视图生成器
- `eva/l1_sensing/history.py`
  - 当前 current-state / append-only history 写入逻辑可继续作为投影层使用

### 2.3 需要重点重塑的模块

以下模块是 Phase A 的主要改造点：

- `eva/l1_sensing/sensing.py`
  - 从当前 snapshot / recent-count 采样，升级为同时支持 state 与 rate 的 sensing 输入层
- `eva/l1_sensing/patrol.py`
  - 从直接执行 `sensing -> judgment -> pressure -> persist` 的串行流程，升级为可接入 signal publication 与 drive update 的编排层
- `eva/lifecycle.py`
  - 保留 heartbeat-first 边界，但要为新的 sensing / drive 通路留出清晰接缝

## 3. 合同冻结

Phase A 期间，应优先冻结以下合同。

### 3.1 Signal contract

最小字段：
- `source`
- `class`：`threat | status | background`
- `payload`
- `captured_at`
- `rate_context`

约束：
- 当前 Phase A 至少冻结 signal publication contract
- `threat` 保留为 future fast-path 的显式类别，但当前不宣称完整 routing layer 已成立
- `status` / `background` 进入 drive update 的读侧语义保留
- urgency semantics 若未进入正式字段，则在 closeout 中明确 defer
- 进入 B0 后，turn details 额外冻结 `signal_batch = {signals, summary}` 作为 L1 -> downstream 最小输入面

### 3.2 Drive state contract

最小要求：
- drive state 是连续值
- 初始 drive 类型限定为：`survival / integrity / continuity / curiosity`
- drive 更新先采用规则型累积与衰减
- drive 不与 pressure table 混为同一主结构

### 3.3 Drive broadcast contract

最小要求：
- 对高层是只读接口
- L3 不能直接改写 drive
- 当前兼容 action path 只能通过兼容接口读取新 drive 状态
- 进入 B0 后，`drive_broadcast` 至少稳定暴露：`captured_at / top_drive / drive_levels / drive_trends`

### 3.4 Runtime gate contract

B0 期间额外冻结：
- `runtime_gate_context.instance_valid`
- `runtime_gate_context.turn_allowed`
- `runtime_gate_context.critical_blocked`
- `runtime_gate_context.conservative_mode`
- `runtime_gate_context.life_state`

它属于 kernel -> downstream 的最小运行边界输入。

### 3.5 Compatibility projection contract

Phase A 期间允许保留以下兼容投影：
- `active_pressures.json`
- `survival_log.jsonl`
- `response_history.jsonl`

但约束是：
- 它们属于 projection / compatibility layer
- 不再代表内部主模型
- 不再扩展为未来控制中心

## 4. 模块级实施方向

### 4.1 `eva/l1_sensing/sensing.py`

当前职责：
- 读取 runtime 文件存在性
- 统计 recent event counts
- 提供 patrol 输入 buckets

Phase A 方向：
- 保留现有输入来源
- 在此基础上补 rate / trend 信息
- 输出从“仅供 judgment 的 dict”升级为“可进入 Signal Bus 的标准化输入”

### 4.2 `eva/l1_sensing/judgment.py`

当前职责：
- 把 sensing 输入映射为 `DimensionSnapshot`
- 生成 `overall_status`、`primary_gap`、`trend`

Phase A 方向：
- 保留 deterministic rule baseline
- 在不破坏当前 healthy / degraded / critical 语义的前提下，逐步接入 state + rate 输入
- 暂不把 judgment 改成黑盒模型

### 4.3 `eva/l2_drive/pressure.py`

当前职责：
- 从 judged gaps 生成 active pressure table
- 维护 pressure id、trend、opened / resolved

Phase A 方向：
- 降级为兼容视图生成器
- pressure 保留为高强度状态的可读投影
- 内部真实主状态迁移到 continuous drive state

### 4.4 `eva/l1_sensing/patrol.py`

当前职责：
- 调度 shallow / deep / full cadence
- 执行 sensing -> judgment -> pressure -> history 全链路

Phase A 方向：
- 继续保留 cadence 组织角色
- 从“直接串行调用完整链路”改为“驱动 sensing / signal publication / drive update 流程”的编排器
- patrol 当前负责发布 normalized signal batch，但不被写成完整 routing engine owner
- 不让 patrol 继续成为未来内部主结构的唯一入口

### 4.5 `eva/l1_sensing/history.py`

当前职责：
- 写入 snapshot、pressure table、pressure transitions、survival history

Phase A 方向：
- 保留为投影层
- 继续负责当前兼容工件落盘
- 不承担 drive 主状态本身

### 4.6 `eva/lifecycle.py`

当前职责：
- heartbeat-first life loop
- patrol work queue
- patrol 后 response 触发

Phase A 方向：
- 保留 heartbeat-first safety
- 保留 `run_tick()` / `run_turn()` 的优先级边界
- 明确新 sensing / drive 通路不能破坏：
  - heartbeat deadline guard
  - instance invalid turn block
  - critical life-state turn block
- 当前 patrol 后直接触发 `response.py` 的路径只保留 compatibility 角色
- 不把当前 patrol 后 response hook 误写成完整 reflex / fast-path routing layer

## 5. 持久化边界

Phase A 期间至少保持以下事实不变：

- `runtime_state.json` 继续只承载 Step 0 / kernel 运行态，不混入 drive / pressure 主模型
- `events.jsonl` 继续作为 append-only lifecycle event stream
- `external_life_snapshot.json`、`active_pressures.json`、`survival_log.jsonl` 可暂时保留为兼容工件
- 新的 drive state 如需落盘，应与 `runtime_state.json` 分离

## 6. 测试冻结点

Phase A 迁移期间，应优先以以下测试作为冻结边界：

### 6.1 语义冻结
- `tests/test_judgment.py`
- `tests/test_pressure.py`
- `tests/test_history.py`

### 6.2 sensing / patrol 冻结
- `tests/test_sensing.py`
- `tests/test_patrol.py`

### 6.3 lifecycle / persistence 安全冻结
- `tests/test_lifecycle.py`
- `tests/test_state.py`

这些测试的作用不是阻止内部重构，而是保证：
- 判断语义不被无意破坏
- 兼容工件仍可持续产出
- heartbeat-first 边界不被新通路破坏

## 7. 实施顺序

推荐顺序：

1. 冻结 Signal / Drive / Broadcast 三个最小合同
2. 在 `sensing.py` 上补齐 state + rate 输入
3. 建立最小 Signal Bus 承载面
4. 引入 continuous drive state 与规则型更新
5. 建立 read-only drive broadcast
6. 让 `pressure.py` / `history.py` 降级为兼容投影
7. 最后再接当前兼容 action path 到新 drive 读取接口

## 8. 完成判据

Phase A implementation contract 完成执行后，至少应成立：
- 现有 heartbeat-first baseline 未回退
- sensing 已同时提供 state 与 rate 信息
- Signal Bus 的最小 publication contract 已形成，并明确区分已实现合同与 deferred routing/urgency 能力
- drive state 已成为内部主状态之一
- drive broadcast 已对高层只读暴露
- 旧 pressure / history / response 工件仍可作为兼容层继续工作
