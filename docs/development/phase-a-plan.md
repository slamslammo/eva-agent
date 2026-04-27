# Phase A 计划

本文档定义当前 **Phase A：L1 / L2 结构升级** 的公开计划。

## 1. 目标

Phase A 的目标不是扩动作，而是先建立一条符合 EVA v0.5 的基础通路：

```text
sensing -> signal classification -> drive update -> drive broadcast
```

在这一阶段，即使 L3 仍只有占位结构，也必须先把 L1 / L2 的骨架搭正确。

## 2. 起点资产

Phase A 不是从零开始。当前仓库已经有以下资产可直接作为起点：

- `eva/l1_sensing/sensing.py`：当前外部信号采样
- `eva/l1_sensing/judgment.py`：当前规则式状态判断
- `eva/l1_sensing/patrol.py`：当前 shallow / deep / full cadence 组织
- `eva/l2_drive/pressure.py`：当前 pressure / viability-gap 视图
- `eva/l1_sensing/history.py`：当前 baseline 历史写入
- `eva/lifecycle.py`、`eva/kernel/instance.py`、`eva/kernel/state.py`、`eva/kernel/config.py`：当前 kernel 运行底盘

这些资产应被重组、扩展和降级，而不是继续被当作最终形态放大。

## 3. 工作包

### A1. 补齐 rate sensing

目标：让系统不只知道“现在怎样”，也知道“正在往哪边滑”。

工作重点：
- 增加最小 rate / trend 观测
- 区分 state 与 rate 证据
- 让后续判断可以使用 trajectory，而不仅是瞬时值

优先关注的信号包括：
- disk depletion trend
- error accumulation trend
- restart / recovery trend
- heartbeat miss trend
- distress / yield trend

### A2. 建立 Signal Bus

目标：统一 L1 的信号合同，并为 fast path / slow path 分流提供承载面。

最小合同应包含：
- `source`
- `class`
- `payload`
- `captured_at`
- `rate_context`

约束：
- `threat` 信号必须可直接进入 fast path
- `status` 与 `background` 信号进入 drive update 与后续 deliberation 输入

### A3. 建立 continuous drive state

目标：把当前 pressure 视图背后的主结构升级为 continuous drive model。

Phase A 的初始 drive 类型限定为：
- survival
- integrity
- continuity
- curiosity

约束：
- drive update 先采用规则型累积与衰减
- drive 为连续值，不是离散 severity 的改名
- 当前 pressure 视图可短期保留，但降级为兼容 / 可读视图

### A4. 建立 read-only drive broadcast

目标：让后续层只通过 broadcast 读取 drive context，而不是直接读 pressure 表。

约束：
- broadcast 对高层是只读接口
- L3 不得直接改写 drive
- 当前 `response.py` 只允许通过兼容方式读取新 drive 接口，不再扩 action repertoire

## 4. 本阶段理论不变量

Phase A 期间必须始终保持：
- heartbeat deadline 不被 ordinary work 抢占
- `threat` 信号可以直达 fast path
- drive state 是连续更新的内部状态，而不是离散跳表的改写版本
- drive broadcast 对高层是只读的
- 当前最小 action path 只保留兼容角色，不继续扩动作谱系

## 5. 本阶段不做的事

Phase A 明确不做：
- 扩当前 minimal action path 的动作谱系
- 提前引入完整 mediator
- 提前引入完整 anchor solver
- 提前把 memory 升级为完整 cognitive memory
- 提前把 LLM 接成架构 prerequisite

## 6. 完成标准

Phase A 完成后，至少应成立：
- 系统具备 state + rate 的最小 L1 能力
- signal 可以按 `threat / status / background` 分流
- drive state 是连续更新的内部状态
- drive broadcast 对高层是只读的
- 当前兼容 action path 仍可运行，但不再是未来扩展中心

## 7. 验证重点

需要重点验证：
- heartbeat deadline 仍不被 ordinary work 抢占
- `threat` 信号可直达 fast path
- drive 不退化回离散跳表伪装
- L3 无法直接写 drive state
- 当前兼容通路可在新 drive 接口下继续工作
