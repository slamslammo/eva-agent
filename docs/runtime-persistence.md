# Step 0 持久化协议

## 1. 目标
Step 0 的持久化只服务生命循环本身：
- 保存当前活跃实例投影
- 保存最近生命体征与状态
- 保存可追溯事件流

不承载复杂记忆、业务上下文或任务结果仓库。

## 2. 目录结构
开发 / 测试默认使用项目内或临时目录，例如：

```text
runtime/
  active_instance.json
  runtime_state.json
  events.jsonl
  eva.lock
```

Linux 长期运行时，建议切到：

```text
/var/lib/eva-agent/
  active_instance.json
  runtime_state.json
  events.jsonl
  eva.lock
```

## 3. `active_instance.json`
用于表达当前合法执行者的最小投影。

建议结构：

```json
{
  "instance_id": "eva-20260415-001",
  "generation": 12,
  "lease_expires_at": "2026-04-15T12:00:15Z",
  "lock_holder": true,
  "updated_at": "2026-04-15T12:00:00Z"
}
```

字段说明：
- `instance_id`：当前实例唯一标识
- `generation`：当前代际编号
- `lease_expires_at`：合法执行身份失效时间
- `lock_holder`：写入时当前实例是否仍持有锁
- `updated_at`：最后一次刷新投影的时间

约束：
- 只有当前持锁实例可以刷新它
- lease 刷新应发生在 heartbeat 成功路径中
- generation 在新实例成功接管时递增

## 4. `runtime_state.json`
用于表达当前可恢复生命状态，而不是完整事件历史。

建议结构：

```json
{
  "life_state": "STABLE",
  "last_heartbeat_at": "2026-04-15T12:00:00Z",
  "last_tick_id": "tick-0003",
  "last_turn_id": "turn-0002",
  "heartbeat_age_sec": 0.2,
  "heartbeat_ok": true,
  "state_io_ok": true,
  "tick_ok": true,
  "consecutive_failures": 0,
  "instance_valid": true,
  "recovering_until": "2026-04-15T12:00:30Z",
  "updated_at": "2026-04-15T12:00:00Z"
}
```

字段约束：
- `life_state`：只允许 `RECOVERING / STABLE / DEGRADED / CRITICAL`
- `heartbeat_age_sec`：以当前时间与最近 heartbeat 成功时间差计算
- `consecutive_failures`：代表连续失败次数
- `recovering_until`：用于恢复窗口判断，可为空

用途：
- 重启后恢复最近生命状态
- turn 读取行为闸门时使用
- 测试断言当前生命体征

## 5. `events.jsonl`
事件日志是可追溯主记录，每行一个 JSON 对象。

推荐事件类型：
- `startup`
- `tick_started`
- `tick_completed`
- `turn_started`
- `turn_completed`
- `heartbeat_written`
- `distress`
- `yield`
- `shutdown`
- `error`

推荐通用字段：

```json
{
  "event_type": "tick_completed",
  "timestamp": "2026-04-15T12:00:00Z",
  "instance_id": "eva-20260415-001",
  "generation": 12,
  "life_state": "STABLE",
  "tick_id": "tick-0003",
  "details": {
    "instance_valid": true,
    "consecutive_failures": 0
  }
}
```

约束：
- 单条事件必须自包含，不依赖上下文拼接才能理解
- 错误事件需记录错误类别与消息
- distress / yield 事件需明确触发原因

## 6. 写入策略
### 原则
- 状态文件：原子写入
- 事件日志：追加写入
- 所有时间一律写 UTC ISO8601

### 原子写入建议
1. 写到同目录临时文件
2. `flush + fsync`
3. `replace` 到正式文件

### 事件追加建议
- 打开 `events.jsonl` 采用 append 模式
- 单次写入一行完整 JSON + `\n`
- 写完 `flush`

## 7. 生命周期与持久化对应关系
- 启动成功：写 `startup` + 初始化 / 更新两个状态文件
- 每次 `tick`：刷新 `active_instance.json` 与 `runtime_state.json`，并记 `tick_completed`
- 每次 `turn`：至少刷新 `runtime_state.json` 中最近 turn 信息，并记 `turn_completed`
- 进入 `CRITICAL`：写 `distress`
- `instance_valid=false`：写 `yield`
- 正常退出：写 `shutdown`

## 8. 测试关注点
- 状态文件不存在时能否自动初始化
- 原子写入后 JSON 是否始终可读
- 多次事件追加是否保持顺序
- lease 刷新后 `active_instance.json` 是否更新
- distress / yield 是否能在失败路径中落盘

## 9. 平台考虑
mac 本地可以完成绝大多数持久化与锁语义开发，但以下内容需要 Linux 最终验证：
- 真实部署路径权限
- systemd 配合启动时的文件拥有者与工作目录
- 长时运行下的文件锁与 crash recovery
