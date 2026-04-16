# Step 1 持久化方案

## 1. 目标
Step 1 的持久化不再只服务“ta 还活着”，而是在不污染 Step 0 生命循环状态边界的前提下，补出外部生命函数所需要的最小派生状态。

这一层要承载的是：
- 当前外部生命体征快照
- 当前 active pressure
- 追加式生存日志

同时要继续保证：
- Step 0 的生命循环状态仍然清楚、可恢复、可测试
- Step 1 的派生状态不会反向污染 heartbeat / `tick` / `turn` 的基础状态
- Step 1 第一轮仍然不是复杂记忆系统、任务仓库或知识库

换句话说：

> Step 0 的持久化解决“本体如何继续存在”；Step 1 的持久化解决“本体如何记住自己最近感知到了什么、判断成什么、形成了哪些压力”。

---

## 2. 与 Step 0 持久化的边界关系
Step 0 已有的持久化协议继续保持不变：
- `active_instance.json`
- `runtime_state.json`
- `events.jsonl`
- `eva.lock`

### 2.1 继续属于 Step 0 的内容
以下内容继续只属于 Step 0：
- 当前合法执行者投影
- 当前 heartbeat 生命状态
- 最近 `tick / turn` 的最小运行状态
- distress / yield / shutdown 等基础生命事件

因此：
- **不把外部生命感知结果塞进 `runtime_state.json`**
- **不把 active pressure 塞进 `runtime_state.json`**
- **不把 Step 1 的追加式生存历史混进 `events.jsonl` 以外的 Step 0 状态文件**

### 2.2 Step 1 新增长出的派生状态
Step 1 新增的持久化对象，只服务外部生命函数：
1. 当前外部生命快照
2. 当前 active pressure 表
3. 追加式生存日志

这些内容与 Step 0 的关系是：
- 依赖 Step 0 提供的基础事件与基础状态
- 但不反向决定 Step 0 的 heartbeat 结果
- 也不改变 `instance_valid` / `life_state` 的定义

---

## 3. 目录结构
开发 / 测试默认继续使用项目内或临时 runtime 目录。

建议在 Step 1 第一轮扩展为：

```text
runtime/
  active_instance.json
  runtime_state.json
  external_life_snapshot.json
  active_pressures.json
  survival_log.jsonl
  events.jsonl
  eva.lock
```

Linux 长期运行时，建议同样位于长期运行目录，例如：

```text
/var/lib/eva-agent/
  active_instance.json
  runtime_state.json
  external_life_snapshot.json
  active_pressures.json
  survival_log.jsonl
  events.jsonl
  eva.lock
```

其中：
- `active_instance.json` / `runtime_state.json` / `events.jsonl` 保持 Step 0 含义
- `external_life_snapshot.json` / `active_pressures.json` / `survival_log.jsonl` 属于 Step 1

---

## 4. `external_life_snapshot.json`
用于表达“当前这一个时刻，eva 对外部生命体征与生命判断的最小快照”。

它是一个覆盖写文件，不是历史仓库。

### 4.1 建议结构

```json
{
  "captured_at": "2026-04-16T12:00:00Z",
  "source_patrol": "shallow",
  "dimensions": {
    "host_continuity": {
      "status": "healthy",
      "evidence": {
        "process_running": true,
        "schedule_drift_sec": 0.2
      }
    },
    "runtime_integrity": {
      "status": "healthy",
      "evidence": {
        "instance_valid": true,
        "runtime_writable": true,
        "recent_yield_count": 0,
        "recent_distress_count": 0
      }
    },
    "resource_state": {
      "status": "degraded",
      "evidence": {
        "disk_free_bytes": 2147483648,
        "runtime_writable": true
      }
    },
    "anomaly_accumulation": {
      "status": "healthy",
      "evidence": {
        "recent_error_count": 0,
        "recent_restart_count": 0
      }
    }
  },
  "overall_status": "degraded",
  "primary_gap": {
    "type": "resource_state",
    "reason": "disk_space_declining"
  },
  "trend": "worsening",
  "updated_at": "2026-04-16T12:00:00Z"
}
```

### 4.2 字段说明
- `captured_at`：本次快照生成时间
- `source_patrol`：本次快照主要由哪一层巡逻生成，允许值：`shallow / deep / full`
- `dimensions`：各生命维度的当前判断与证据
- `overall_status`：整体外部生命状态，允许值：`healthy / degraded / critical`
- `primary_gap`：当前主缺口
- `trend`：整体趋势，允许值：`improving / stable / worsening / unknown`
- `updated_at`：最后一次成功写入时间

### 4.3 约束
- 只保存**当前**快照，不保存历史版本
- `dimensions` 第一轮只允许包含：
  - `host_continuity`
  - `runtime_integrity`
  - `resource_state`
  - `anomaly_accumulation`
- 单次快照必须自包含，可脱离其他文件单独理解
- 第一轮只覆盖宿主 / 本地 / runtime 层

---

## 5. `active_pressures.json`
用于表达“当前仍然 active 的生存压力项集合”。

它是一个覆盖写文件，代表当前激活压力表，不是完整历史归档。

### 5.1 建议结构

```json
{
  "captured_at": "2026-04-16T12:00:00Z",
  "pressures": [
    {
      "pressure_id": "pressure-resource_state-disk_space_declining",
      "type": "resource_state",
      "severity": "degraded",
      "evidence": {
        "disk_free_bytes": 2147483648,
        "runtime_writable": true
      },
      "first_seen_at": "2026-04-16T10:00:00Z",
      "last_seen_at": "2026-04-16T12:00:00Z",
      "trend": "worsening",
      "active": true
    }
  ],
  "updated_at": "2026-04-16T12:00:00Z"
}
```

### 5.2 字段说明
- `captured_at`：本次压力表刷新时间
- `pressures`：当前 active 的压力项数组
- `updated_at`：最后一次成功写入时间

#### 单个 pressure 的最小字段
- `pressure_id`：稳定 ID，用于跨次刷新识别同一压力
- `type`：允许值：
  - `continuity`
  - `resource_state`
  - `integrity`
  - `anomaly_accumulation`
- `severity`：允许值：`healthy / degraded / critical`
- `evidence`：触发当前压力的最小证据
- `first_seen_at`：首次出现时间
- `last_seen_at`：最近一次仍观察到该压力的时间
- `trend`：`improving / stable / worsening / unknown`
- `active`：第一轮固定为 `true`，表示该文件中存在的项仍为当前激活项

### 5.3 约束
- 文件中只保留当前 active 的压力项
- 一旦某个压力不再 active，不在本文件保留历史墓碑
- 历史变化应进入 `survival_log.jsonl`
- `pressure_id` 应尽量稳定，使同一类压力在多次巡逻之间能被识别为同一项
- Step 1 第一轮压力不直接等于任务，不包含执行计划字段

---

## 6. `survival_log.jsonl`
用于表达“最近一段时间 eva 的外部生命体征、生命判断与压力变化的追加式生存历史”。

它是 Step 1 的最小历史记录主文件。

### 6.1 建议结构
每行一个 JSON 对象，例如：

```json
{
  "event_type": "survival_snapshot",
  "timestamp": "2026-04-16T12:00:00Z",
  "source_patrol": "deep",
  "overall_status": "degraded",
  "primary_gap": {
    "type": "resource_state",
    "reason": "disk_space_declining"
  },
  "trend": "worsening",
  "active_pressure_ids": [
    "pressure-resource_state-disk_space_declining"
  ],
  "details": {
    "dimension_status": {
      "host_continuity": "healthy",
      "runtime_integrity": "healthy",
      "resource_state": "degraded",
      "anomaly_accumulation": "healthy"
    },
    "summary": "disk space is declining while runtime remains stable"
  }
}
```

### 6.2 推荐事件类型
第一轮只需要三类：
- `survival_snapshot`
- `pressure_opened`
- `pressure_resolved`

其中：
- `survival_snapshot`：记录一次 deep patrol 或 full report 之后的阶段性外部生命快照
- `pressure_opened`：记录某个压力第一次进入 active 表
- `pressure_resolved`：记录某个压力从 active 状态退出

### 6.3 通用字段
- `event_type`
- `timestamp`
- `source_patrol`（如果事件来自某次巡逻）
- `overall_status`
- `primary_gap`
- `trend`
- `active_pressure_ids`
- `details`

### 6.4 约束
- 单条日志必须自包含，不依赖上下文才能理解
- 只记录对 Step 1 生存回顾有意义的信息
- 不退化成完整原始事件镜像仓库
- 第一轮无需支持语义检索、索引或复杂聚合

---

## 7. 与 `events.jsonl` 的关系
Step 0 的 `events.jsonl` 继续作为本体运行事件的可追溯主记录。

Step 1 不应复制整份事件流，而应：
- 从 `runtime_state.json` / `events.jsonl` / 本地文件系统中采样
- 生成更高一层的外部生命快照、压力表与追加式生存日志

### 7.1 `events.jsonl` 继续承担的角色
- 记录 `startup / tick_started / tick_completed / turn_started / turn_completed / distress / yield / shutdown`
- 为 Step 1 提供原始可追溯证据

### 7.2 Step 1 三个新文件承担的角色
- `external_life_snapshot.json`：当前态
- `active_pressures.json`：当前激活压力
- `survival_log.jsonl`：阶段性历史

### 7.3 原则
- 原始运行事件不搬家
- 派生生命判断单独落盘
- 当前态与历史态分离

---

## 8. 写入策略
### 8.1 原则
- 当前状态类文件：原子写入
- 追加式日志：append 写入
- 所有时间统一写 UTC ISO8601

### 8.2 状态类文件
以下文件采用原子写入：
- `active_instance.json`
- `runtime_state.json`
- `external_life_snapshot.json`
- `active_pressures.json`

建议流程：
1. 写入同目录临时文件
2. `flush + fsync`
3. `replace` 到正式文件

### 8.3 追加式日志
以下文件采用 append 写入：
- `events.jsonl`
- `survival_log.jsonl`

建议流程：
1. append 模式打开
2. 单次写入一行完整 JSON + `\n`
3. `flush`

---

## 9. 生命周期与持久化对应关系
### shallow patrol 完成后
- 刷新 `external_life_snapshot.json`
- 如压力表发生变化，刷新 `active_pressures.json`
- 第一轮不强制 shallow 每次都写 `survival_log.jsonl`

### deep patrol 完成后
- 刷新 `external_life_snapshot.json`
- 刷新 `active_pressures.json`
- 追加一条 `survival_snapshot` 到 `survival_log.jsonl`
- 若有新 pressure 打开或旧 pressure 关闭，追加 `pressure_opened / pressure_resolved`

### full report 完成后
- 刷新 `external_life_snapshot.json`
- 刷新 `active_pressures.json`
- 追加一条更完整的 `survival_snapshot`
- 必要时追加 `pressure_opened / pressure_resolved`

### Step 0 生命周期事件
继续保持：
- 启动成功：写 `startup`
- 每次 `tick`：刷新 `active_instance.json` 与 `runtime_state.json`
- 每次 `turn`：按原协议刷新 `runtime_state.json`
- 进入 `CRITICAL`：写 `distress`
- `instance_valid=false`：写 `yield`
- 正常退出：写 `shutdown`

---

## 10. 第一轮不做的持久化内容
以下内容明确不进入 Step 1 第一轮：
- 网络 / API 依赖状态仓库
- 复杂任务队列持久化
- 语义检索索引
- 经验知识库
- skill 仓库
- 自我改写记录
- LLM 上下文仓库
- 多版本报告目录树

原因：Step 1 的持久化目标是形成最小外部生命函数状态，而不是提前长成完整记忆系统。

---

## 11. 测试关注点
### 11.1 状态边界
- `runtime_state.json` 不应出现 Step 1 pressure / snapshot 字段
- `external_life_snapshot.json` 与 `active_pressures.json` 应可单独读取并自解释

### 11.2 当前态与历史态分离
- 覆盖写快照不应破坏追加式历史
- active pressure 表更新不应丢掉历史 opened / resolved 记录

### 11.3 压力稳定性
- 同一类压力跨次巡逻应保持稳定 `pressure_id`
- 已消失压力应从 `active_pressures.json` 删除，但在 `survival_log.jsonl` 留下 resolved 记录

### 11.4 Step 0 非回归
- `active_instance.json` / `runtime_state.json` / `events.jsonl` 的现有语义不变
- bounded run 与现有测试结构不被破坏

### 11.5 Linux 补验证
需要在 Linux 长时运行下确认：
- Step 1 新文件权限与路径正常
- 追加式生存日志可持续写入
- 长时运行时快照与压力表持续更新

---

## 12. 一句话收口

> Step 1 的持久化应把“当前外部生命状态”“当前 active pressure”和“追加式生存历史”分开保存，让 eva 开始记住自己最近感知到了什么、判断成什么、形成了哪些压力，同时不污染 Step 0 的生命循环状态边界。
