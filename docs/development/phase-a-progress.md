# Phase A 进展

本文档记录当前 **Phase A：L1 / L2 结构升级** 的进展。

## 1. 当前状态

- 日期：2026-04-28
- 阶段状态：**A5 strict closeout / audit 进行中**
- 判断：A1 ~ A4 主干已经落地并通过现阶段回归，但当前仍在收紧合同、补 targeted verification、修正文档口径，暂不直接宣告 Phase A 正式关闭

## 2. 已完成工作

### 前置整理
- 公开文档已按 EVA v0.5 主线完成重构
- 已建立 `docs/architecture.md` 作为公开总方案
- 已建立 `docs/development/roadmap.md`
- 已建立当前 Phase A 的计划、实施合同与进展文档
- 旧 baseline / runbook / governance 文档已退出公开主线

### A1：state + rate sensing
- 在现有 sensing 输入上补齐最小 rate / trend 信息
- `rate_context` 已进入 judgment 语义，而不再只是附属字段
- severity 判断已能体现 trajectory-sensitive 差异

### A2：Signal Bus / signal publication contract
- 已建立最小 Signal Bus 合同：`source / class / payload / captured_at / rate_context`
- patrol 现在会产出标准化 signal batch
- lifecycle turn details 已暴露 `signal_summary`
- 当前已明确：Phase A 冻结的是 normalized signal publication contract，而不是完整 routing layer

### A3：continuous drive state
- 已建立 `DriveState` / `DriveStateTable`
- 已新增独立的 `drive_state.json` 作为 L2 durable current-state artifact
- patrol 后会执行规则型 drive update，并持久化最新 drive state
- lifecycle turn details 已暴露 `drive_summary`

### A4：read-only drive broadcast
- 已在 `eva.l2_drive` 建立显式只读 broadcast surface
- 已新增 `DriveBroadcast` 与 `build_drive_broadcast()`
- patrol 结果已显式携带 `drive_broadcast`
- lifecycle turn details 已暴露 `drive_broadcast`
- 当前兼容 response path 已能以只读 `drive_context` 形式读取新 drive 接口
- response 仍不拥有 drive update / write 权限

## 3. 当前已确认的结构状态

### 已稳定保留的底盘
- kernel baseline：heartbeat-first、`tick / turn`、`instance_valid`、distress / yield
- patrol cadence 与 bounded runtime 验证路径
- current-state 原子写入与 append-only history/event 模式

### 已形成的 L1 / L2 主干
- sensing -> judgment -> signal classification -> drive update -> drive broadcast
- drive 已成为独立的连续内部状态，而非 pressure severity 的改名
- broadcast 已作为当前 downstream 的只读读取面暴露
- patrol 后 response 仍是 pressure-led compatibility path，不应被理解为 drive-native downstream policy

### 仍保留为 compatibility projection 的工件
- `active_pressures.json`
- `survival_log.jsonl`
- `response_history.jsonl`

这些工件仍可运行，但语义上已降级为 projection / compatibility layer，而不是内部主模型。

## 4. 关键验证结果

### A4 定向验证
已通过：

```bash
PYTHONPATH="/Users/mojiawen/Documents/claude_projects/eva-agent" python -m unittest \
  tests.test_drive \
  tests.test_patrol \
  tests.test_lifecycle \
  tests.test_response \
  tests.test_main_loop
```

结果：`31 tests, OK`

### A5 strict closeout 回归
已通过：

```bash
PYTHONPATH="/Users/mojiawen/Documents/claude_projects/eva-agent" python -m unittest \
  tests.test_drive \
  tests.test_patrol \
  tests.test_lifecycle \
  tests.test_response \
  tests.test_main_loop \
  tests.test_state \
  tests.test_pressure \
  tests.test_sensing \
  tests.test_judgment \
  tests.test_history
```

结果：`55 tests, OK`

## 5. 已确认未被破坏的边界

- heartbeat deadline guard 仍先于 ordinary turn work
- instance invalid block 与 critical state block 仍保留
- `runtime_state.json` 仍只承载 kernel / Step 0 运行态
- `drive_state.json` 是当前唯一 durable L2 主状态文件
- response 仍通过 compatibility path 触发，不扩动作谱系
- L3 / response 仍不能写 drive

## 6. 下一步

A5 当前仍在进行中。

下一步应继续：
1. 冻结 Signal Bus publication contract 与 deferred routing/urgency 边界
2. 补 temporal drive behavior、broadcast canonical usage、response boundary 的 targeted verification
3. 完成 README / architecture / roadmap / phase-a docs 的 strict closeout 对齐
4. 在上述收尾完成后，再判断是否正式关闭 Phase A 并进入 Phase B 规划与实施准备
