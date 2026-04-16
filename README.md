# eva-agent

自主生存 / 自我成长 agent 实验工程。

## 项目定位
`eva-agent` 不是一个先追求功能强大、再补成长能力的通用 agent，也不是一个默认以“服务用户完成任务”为第一原则的 agent。

这个项目的起点是：
- 先建立一个可持续存在的生命循环
- 再用生命函数评估生命体征
- 再在其上逐步长出记忆、技能与判断偏好

项目要验证的是：agent 的关键能力能不能不是被一次性设计完，而是在真实运行、真实反馈和真实压力下逐步成长出来。

## 当前阶段
当前处于：Step 1（第一轮本地实现、本地测试、Linux accelerated 验证与 Linux 异常注入验证已完成；真实生产节律长期观察待补）

当前已确认：
- 起点是生命循环，不是功能列表
- 生命函数分为外部生命函数和内部生命函数两层
- 生命循环采用带 heartbeat deadline 的事件驱动主循环
- heartbeat 是生命节律，不等于任务处理
- `tick` 与 `turn` 分离；生命信号、外部信号、时间信号、内源信号在同一主循环内协同
- heartbeat 的最小 `tick` 序列已固定：醒来 → 刷新合法性投影 → 采样生命体征 → 运行内部生命函数 → 写 heartbeat 与状态快照 → 必要时发出最小求救信号 → 安排下一个 deadline
- Step 0 的基础 heartbeat 时间尺度已固定：15 秒脉搏；约 45 秒进入 `DEGRADED`；约 135 秒进入 `CRITICAL`
- 5 分钟 / 30 分钟 / 24 小时保留为 Step 1 的巡逻与报告节律，不混入 Step 0 heartbeat
- turn 的最小处理序列已固定：醒来记录触发来源 → 检查 heartbeat deadline → 读取生命状态 → 行为闸门判断 → 选取一个 work slice → 执行 → 落盘 → 返回主循环
- `instance_valid` 的最小思路已固定：用 lock + generation + lease_expiry 投影“当前是否仍被承认为合法执行者”
- Step 0 的最小运行壳边界已固定：supervisor 配合层 + 单实例合法性层 + 事件驱动主循环层 + 基础 heartbeat 层 + turn 执行层 + 状态持久化层 + 最小 distress / yield 机制

## 当前非目标
Step 0 暂不讨论：
- 复杂工具系统
- 多渠道交互
- 经济系统与收入模型
- skill 自动生成
- LoRA / 蒸馏落地
- 复杂长期记忆检索

这些属于后续阶段，不应在生命循环未固定前提前展开。

## 文档入口
- `docs/project-definition.md`：项目定义、设计哲学与当前边界
- `docs/development-standards.md`：后续迭代中的开发规范、代码质量要求与变更纪律
- `docs/step-0-life-loop.md`：Step 0 生命循环、双层生命函数与最小生命体征规格
- `docs/step-0-implementation-spec.md`：Step 0 的模块边界、事件流与状态流
- `docs/runtime-persistence.md`：`active_instance.json`、`runtime_state.json`、`events.jsonl` 的持久化协议
- `docs/step-0-verification.md`：单测、smoke test 与 Linux 补验证方案
- `docs/deploy-systemd-example.md`：Linux 长期运行的最小部署示例
- `docs/reference-materials.md`：原始 Obsidian 材料路径与回顾入口
- `docs/step-1-outline.md`：Step 1 巡逻与报告层的启动说明
- `docs/step-1-implementation-spec.md`：Step 1 的能力推导、能力边界、归类原则与第一轮实现收口
- `docs/step-1-persistence.md`：Step 1 的快照、active pressure 与追加式生存日志持久化方案
- `docs/step-1-verification.md`：Step 1 的非回归验证、本地 accelerated cadence 验证与 Linux 长时运行验证方案

## 下一关键节点
- 已完成 Step 0 的实现合同文档与最小 Python 运行壳骨架
- 已完成 `config.py`、`state.py`、`instance.py`、`lifecycle.py`、`main.py` 与基础测试
- 已通过 mac 本地 bounded run、自动化测试与结构化日志验证核心边界
- 已在远程 Linux 主机以 user systemd 方式完成隔离部署与基本验证
- 已完成长时 heartbeat 观察，以及 generation mismatch / lease expiry / restart recovery / distress injection 的异常路径验证
- 已补 Step 1 启动说明、实现规格、持久化方案、验证方案与原始参考材料入口，支持新会话直接继续 Step 1 docs-first 规划
- 已完成 Step 1 第一轮本地实现：external life sensing、judgment、pressure、history、patrol 调度已接入 heartbeat-first 主循环
- 已完成 Step 1 本地自动化验证：34 个测试通过，覆盖 Step 0 非回归、Step 1 模块边界、pressure 开关历史与 accelerated cadence 集成路径
- 已在远程 Linux 主机同步 Step 1 代码并通过全量测试
- 已在远程 Linux 主机通过 accelerated 验证：journal 中观察到 shallow / deep / full patrol，runtime 目录真实生成 `external_life_snapshot.json`、`active_pressures.json`、`survival_log.jsonl`
- 已在远程 Linux 主机通过半真实节律观察：5s / 10s / 15s cadence 下持续观察到 shallow / deep / full 触发，heartbeat 未被 patrol 压住
- 已在远程 Linux 主机通过异常注入验证：通过移除再恢复 `eva.lock` 路径，真实得到 `pressure_opened -> pressure_resolved` 历史链路
- 下一步只剩真实生产节律的长期观察，以及决定是否进行 Step 1 收口提交
