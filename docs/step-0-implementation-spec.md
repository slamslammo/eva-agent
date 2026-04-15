# Step 0 实现规格

## 1. 目标
Step 0 的实现目标不是做一个功能型 agent，而是实现一个**最小但真实可运行的生命循环**，让 `eva-agent` 具备：
- 持续运行的主循环
- 基础 heartbeat 节律
- 单实例合法性投影
- 状态持久化
- 在异常或失去合法执行权时主动让渡

这一版只验证“本体能否稳定活着”，不验证更高层能力。

## 2. 本轮边界
### 必须包含
- 单进程、单实例、同步运行壳
- heartbeat deadline 驱动的主循环
- `tick` 与 `turn` 分离
- `instance_valid = lock_held AND generation_matches AND lease_not_expired`
- `runtime_state.json` / `active_instance.json` / `events.jsonl` 持久化
- distress / yield 的最小事件落盘
- bounded run 模式，便于本地开发与测试

### 明确不包含
- LLM 调用
- 外部 API 巡逻
- 多工具系统
- 复杂记忆检索
- 多线程 / asyncio
- Step 1 的 `5m / 30m / 24h` 巡逻层
- supervisor 本体实现

## 3. 模块划分

## 3.1 `eva/config.py`
职责：
- 固定 heartbeat、lease、退化阈值、默认路径
- 提供测试用加速参数
- 提供 bounded run 参数

建议核心结构：
- `EvaPaths`：运行目录与关键文件路径
- `LifecycleConfig`：heartbeat、lease、状态阈值、recovering 窗口
- `LoopControl`：最大 tick 数、最大 turn 数、最大运行时长
- `build_runtime_paths(base_dir)`：从 runtime 根目录构造文件路径

## 3.2 `eva/state.py`
职责：
- 初始化 runtime 目录
- 读取 / 写入 `runtime_state.json`
- 读取 / 写入 `active_instance.json`
- 追加 `events.jsonl`

约束：
- 所有写入先写临时文件再原子替换
- 事件日志采用 json line 追加，单条事件自包含
- 状态对象以 dataclass 表示，再序列化为 JSON

## 3.3 `eva/instance.py`
职责：
- 获取并持有 lock
- 初始化 / 刷新 active instance 投影
- 比对 generation
- 基于 lock、generation、lease 判断 `instance_valid`

约束：
- 第一版以 Linux/macOS 均可用的 `fcntl.flock` 为主
- `generation` 由当前 active instance 文件递增得到
- lease 刷新放在 heartbeat 路径内完成
- 一旦 `instance_valid=false`，只允许最小收尾路径

## 3.4 `eva/lifecycle.py`
职责：
- 采样生命体征
- 运行内部生命函数
- 执行 `tick`
- 执行 `turn`
- 在必要时记录 distress / yield 事件

边界：
- `tick` 是短路径，只处理生命体征，不处理普通任务
- `turn` 一次只处理一个 work slice
- `turn` 遇到 heartbeat deadline 临近时必须让位

## 3.5 `eva/main.py`
职责：
- 初始化配置、paths、state store、instance guard
- 启动主循环
- 在 heartbeat deadline、外部信号、内源信号之间做最小调度
- 提供 CLI 入口与 bounded run 模式

第一版主循环策略：
- 不引入真实消息系统
- 用内存中的 pending work slices 队列模拟普通 `turn`
- heartbeat 优先级始终高于普通 `turn`

## 4. 关键数据流

### 4.1 启动
1. 初始化 runtime 目录
2. 获取文件锁
3. 读取当前 active instance
4. 生成新的 `instance_id` 与 `generation`
5. 写入新的 `active_instance.json`
6. 初始化或恢复 `runtime_state.json`
7. 写入 `startup` 事件
8. 进入主循环

### 4.2 tick
1. 记录 `tick_started`
2. 刷新合法性投影
3. 采样生命体征
4. 计算 `life_state`
5. 刷新 lease 与 heartbeat
6. 写入 `runtime_state.json`
7. 追加 `tick_completed` 事件
8. 若进入 `CRITICAL` 或 `instance_valid=false`，追加 distress / yield 事件

### 4.3 turn
1. 记录 `turn_started`
2. 检查 heartbeat deadline
3. 读取当前 `life_state` 与 `instance_valid`
4. 通过行为闸门决定是否允许普通 turn
5. 只执行一个 work slice
6. 写入 turn 结果与后续信号
7. 返回主循环

## 5. 行为闸门
- `RECOVERING`：只允许自检或极短 work slice
- `STABLE`：允许普通 turn
- `DEGRADED`：只允许高优先级 turn，暂停非必要内源任务
- `CRITICAL`：普通 turn 停止，只允许 distress、yield、状态落盘
- `instance_valid=false`：视为硬停止普通 turn

## 6. 第一版 work slice
第一版只实现一个最小占位 work slice，例如：
- `noop`
- `self_check`
- `persist_marker`

目的不是完成业务，而是证明：
- 主循环能在 heartbeat 之间调度普通 turn
- 普通 turn 可被 heartbeat 抢占
- turn 结果能落盘并可追踪

## 7. bounded run 设计
为适配 mac 本地开发和自动化测试，主循环必须支持 bounded run：
- 限制最大 tick 数
- 限制最大 turn 数
- 限制最大运行时长
- 可注入加速 heartbeat 参数
- 可指定 runtime 临时目录

这使得：
- 单元测试不依赖真实长期运行
- mac 上也能稳定验证 Step 0 核心边界
- Linux 上再补长期运行与部署验证

## 8. Linux 与 mac 的验证分工
### mac 本地适合
- 数据结构与状态落盘开发
- `tick` / `turn` 行为测试
- `fcntl` 基础锁语义测试
- bounded smoke test

### 必须在 Linux 补验证
- 长期运行行为
- `/var/lib/eva-agent/` 之类真实路径权限
- systemd 守护启动
- 文件锁与进程恢复在目标环境下的稳定性
- 长时间 heartbeat 与 lease 刷新

## 9. 完成判据
本轮实现完成时，应满足：
- 能通过 CLI 在临时 runtime 目录启动 bounded 主循环
- 能连续写出 heartbeat 与状态快照
- 能正确投影 `instance_valid`
- `tick` / `turn` 边界有自动化测试
- 异常或失效时会停止普通 turn 并写出 distress / yield 事件
