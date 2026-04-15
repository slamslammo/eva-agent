# Step 0：生命循环

## 1. Step 0 的目标
Step 0 只解决一件事：

**让 eva 成为一个可持续存在的运行体，而不是一次性的 AI 调用。**

这一阶段先不讨论成长、赚钱、复杂工具或完整 agent 功能，而是先定义：
- ta 怎么持续运行
- ta 怎么证明自己还活着
- ta 挂掉后怎么回来
- ta 重启后怎么保持连续性

## 2. 两层生命函数
### 2.1 外部生命函数
外部生命函数由设计者 / 宿主 / 守护系统视角定义。

它关心：
- eva 是否仍作为唯一生命体存在
- 是否满足单实例约束
- 是否出现多实例重影
- 重启后是否仍是合法延续
- 守护、恢复、代际是否正常

这层关注的是存在论意义上的连续性，不是当前本体自己完全能决定的。

### 2.2 内部生命函数
内部生命函数由当前运行中的 eva 本体视角定义。

它只看当前这一代本体在运行时此刻能直接观察到的事实，或能接收到的合法性信号投影。

它关心：
- 我的 loop 还在稳定运行吗
- 我的 heartbeat 还在成功写出吗
- 我的状态还能正常持久化吗
- 我的失败是否在持续累积
- 我当前是否仍是被承认的合法实例

## 3. 生命循环的结构
### 3.1 heartbeat 与任务处理不是一回事
heartbeat 是生命节律，不等于任务处理。

为了避免混淆，需要区分：

#### tick
一次 heartbeat 拍点。主要负责：
- 体征采样
- 生命函数评估
- 状态写入
- heartbeat 写出

#### turn
一次被唤醒后的处理轮次。它可能由外部请求、定时任务、内源任务或 heartbeat 到点触发。

### 3.2 当前确认的主循环结构
Step 0 的生命循环采用：

**带 heartbeat deadline 的事件驱动主循环**

也就是：
- 外层是一个持续运行的事件驱动主循环
- heartbeat 有自己的硬性 deadline
- 外部信号、时间信号、内源信号都在同一主循环内进入
- 普通任务不能长期阻塞 heartbeat

## 4. 信号分层
当前把主循环中的输入信号分为四类：

### 4.1 生命信号
- heartbeat 是否成功
- tick 是否完整
- 状态是否可持久化
- 连续失败是否升高
- 当前实例是否合法

### 4.2 外部信号
- 用户请求
- webhook / message
- 环境变化
- 外部任务触发

### 4.3 时间信号
- cron 到期
- maintenance 窗口到期
- 周期性检查
- 定时报告

### 4.4 内源信号
- 自检
- 反思
- 记忆整理
- 修复任务
- 自我提出的问题

## 5. 内部生命体征最小指标集
当前已确认的内部最小指标集：

1. `heartbeat_ok`
   - 本轮 heartbeat 是否成功写出

2. `heartbeat_age`
   - 距离上次成功 heartbeat 的时间

3. `state_io_ok`
   - 状态文件读写是否正常

4. `tick_ok`
   - 本轮主循环是否完整结束

5. `consecutive_failures`
   - 当前连续失败次数

6. `instance_valid`
   - 当前 lease / generation / lock 投影出来的实例合法性是否仍有效

## 6. 内部生命状态
内部生命函数当前使用 4 个状态：
- `RECOVERING`
- `STABLE`
- `DEGRADED`
- `CRITICAL`

### 6.1 STABLE
生命体征正常，当前循环处于稳态。

### 6.2 DEGRADED
还活着，但生命体征已有退化。

### 6.3 CRITICAL
关键生命体征失守，本体不适合继续正常运行。

### 6.4 RECOVERING
重启或恢复窗口内，尚未重新进入稳态。

## 7. 生命函数的作用
内部生命函数不只是输出状态，还应作为行为闸门：
- `STABLE`：允许正常处理外部、时间和部分内源任务
- `DEGRADED`：开始限流，优先保全自身
- `CRITICAL`：暂停普通任务，只保留求救、持久化、自我修复或向 supervisor 让渡控制
- `RECOVERING`：先恢复与自检，再恢复正常处理

## 8. Step 0 当前已定项
### 8.1 宿主环境方向
为了支持长期运行测试，第一版不采用本地长期运行，而采用：
- 云主机，或
- 其他可长期运行的 Linux 机器

默认环境假设优先为：
- Ubuntu
- bash 环境

### 8.2 实现语言方向
第一版 agent 运行壳优先采用 Python 实现。

### 8.3 heartbeat 的最小 tick 序列
heartbeat 的 `tick` 是生命节律拍点，不承担普通任务处理。

第一版最小 tick 序列固定为：
1. **醒来**
   - 由 heartbeat deadline 触发一次 tick
   - 记录当前时间、tick_id、wake_reason=heartbeat
2. **刷新合法性投影**
   - 读取当前实例的 lease / generation / lock 投影结果
   - 刷新 `instance_valid`
3. **采样最小生命体征**
   - 采样 `heartbeat_age`
   - 检查 `state_io_ok`
   - 检查上一轮 `tick_ok`
   - 检查 `consecutive_failures`
   - 检查是否处于恢复窗口
4. **运行内部生命函数**
   - 基于当前采样结果判断 `RECOVERING / STABLE / DEGRADED / CRITICAL`
5. **写 heartbeat 与状态快照**
   - 追加一次 heartbeat 事件
   - 持久化当前 life_state、关键指标和 tick 结果
6. **必要时发出最小求救信号**
   - 如果进入 `CRITICAL` 或 `instance_valid=false`
   - 发出最小 distress / yield 信号
   - 该步骤是 best-effort，不应阻塞 heartbeat 落盘
7. **安排下一个 heartbeat deadline**
   - 更新下一次 tick 的预定时间
   - 返回事件驱动主循环

### 8.4 tick 的边界约束
为保证 heartbeat 真正代表生命节律，第一版 tick 必须满足：
- **短**：tick 必须是短路径，不能包含长耗时处理
- **本地优先**：核心路径优先依赖本地时间、状态文件和本地合法性投影
- **不依赖 LLM**：tick 不调用模型，不做复杂推理
- **不处理普通任务**：外部请求、定时任务、反思与整理不在 tick 内执行
- **不能被普通任务长期阻塞**：普通 turn 只能在 heartbeat deadline 之间占用有限 work slice

### 8.5 Step 0 基础 heartbeat 默认时间尺度
Step 0 的 heartbeat 是**基础生命脉搏**，不是巡逻任务。

第一版默认建议值：
- `base_heartbeat_interval_sec = 15`
- `degraded_after_missed_beats = 3`（约 45 秒）
- `critical_after_missed_beats = 9`（约 135 秒）

含义：
- 15 秒一次 heartbeat，代表本体仍在持续运行
- 连续错过 3 次基础 heartbeat，内部生命状态进入 `DEGRADED`
- 连续错过 9 次基础 heartbeat，内部生命状态进入 `CRITICAL`

这里的 heartbeat 只负责生命脉搏，不承担钱包、API、记忆完整性等更高层巡逻职责。

### 8.6 Step 1 巡逻节律候选（暂不纳入 Step 0）
以下节律保留为 Step 1 survival agent 的候选巡逻层，而不是 Step 0 heartbeat 本身：

#### shallow patrol
- `interval_sec = 300`（5 分钟）
- `timeout_sec = 600`（10 分钟）
- 用于轻量本地巡逻：进程、文件、基础状态一致性

#### deep patrol
- `interval_sec = 1800`（30 分钟）
- `timeout_sec = 3600`（60 分钟）
- 用于完整生存巡逻：关键外部依赖、钱包/API、关键记忆文件完整性

#### full report
- `interval_sec = 86400`（24 小时）
- `timeout_sec = 7200`（2 小时）
- 用于完整生命函数评估与外部报告

结论：
- `15s / 45s / 135s` 属于 Step 0 的基础生命脉搏
- `5m / 30m / 24h` 属于 Step 1 之上的巡逻与报告节律
- 两者不是互斥关系，而是不同层级的时间尺度

### 8.7 turn 的最小处理序列
`turn` 是一次被唤醒后的最小处理轮次，用来承接外部信号、时间信号和内源信号；它不是 heartbeat 本身。

第一版最小 turn 序列固定为：
1. **醒来并记录触发来源**
   - 记录 `turn_id`
   - 记录 `wake_reason`（external / scheduled / endogenous）
2. **快速检查 heartbeat deadline 是否临近**
   - 如果已到 heartbeat 时点，优先让位给 tick
   - 如果距离下一次 heartbeat 过近，则只允许极短处理或直接返回主循环
3. **读取当前生命状态**
   - 读取最近一次 `life_state`
   - 读取 `instance_valid`
   - 读取当前是否处于 `RECOVERING / DEGRADED / CRITICAL`
4. **做行为闸门判断**
   - `STABLE`：允许处理普通 turn
   - `DEGRADED`：只允许高优先级 turn，暂停非必要内源任务
   - `CRITICAL`：普通 turn 不执行，只允许求救、让渡、恢复相关动作
   - `RECOVERING`：优先恢复和最小自检，限制普通 turn
5. **选取一个 work slice**
   - 一次 turn 只处理一个最小任务切片
   - 不追求在一个 turn 内完成整条长链路
6. **执行该 work slice**
   - 允许执行普通任务逻辑
   - 但必须可中断、可落盘、可在下一个 turn 续接
7. **落盘结果与后续信号**
   - 记录本次 turn 的输入、结果、错误或未完成状态
   - 如有后续动作，生成新的 scheduled / endogenous 信号，而不是在当前 turn 无限延长
8. **返回事件驱动主循环**
   - 把控制权还给主循环，等待下一个信号或 heartbeat deadline

### 8.8 turn 的边界约束
第一版 turn 必须满足：
- **一次只做一个 work slice**：避免长链路无限占用主循环
- **必须可续接**：未完成的工作要能在后续 turn 恢复
- **必须可让位给 heartbeat**：heartbeat deadline 优先级高于普通 turn
- **允许普通任务，但不允许无限执行**：turn 不是 while-loop inside while-loop
- **允许失败，但失败必须落盘**：失败不能只停留在内存里

### 8.9 `instance_valid` 的定义
`instance_valid` 是一个内部可读的合法性投影信号，用来回答：

**当前这一代 eva 实例，是否仍被外部生命约束承认为唯一且合法的执行者。**

它不回答：
- 世界上有没有另一个自己
- 心跳停止后是否会被复制
- 整个系统是否已经完成代际切换

它只回答一个更小且更实用的问题：

**我现在还能不能继续代表 eva 行动。**

### 8.10 `instance_valid` 的最小投影机制
Step 0 在单台长期在线 Linux 机器前提下，最小投影机制采用三件东西：

#### A. lock
用于保证同一时刻只有一个活动实例持有行动权。

最小实现：
- OS 级文件锁（如 `flock` 或 Python 文件锁）
- 固定锁文件路径，例如：`/var/lib/eva-agent/eva.lock`

它回答：
- 我当前是否仍持有行动权

#### B. generation
用于区分当前代与过期代。

最小实现：
- 持久化一个递增的 `generation`
- 每次合法重启或新实例接管时递增
- 当前实例在启动时记住自己的 `generation`

它回答：
- 我是不是当前这一代，而不是旧代残留实例

#### C. lease_expiry
用于把合法性变成有时效的承认。

最小实现：
- 当前实例在 heartbeat 中刷新 `lease_expires_at`
- 如果长时间未刷新，即使某个实例仍在某处运行，也应视为失效

它回答：
- 我当前的合法身份是否已过期

### 8.11 `instance_valid` 的第一版判断公式
第一版直接收敛为：

`instance_valid = lock_held AND generation_matches AND lease_not_expired`

也就是：
- 我仍持有 lock
- 我的 generation 与当前 active generation 一致
- 我的 lease 仍未过期

三者同时成立，`instance_valid=true`；任一失效，`instance_valid=false`。

### 8.12 最小状态投影载体
第一版建议使用一个最小持久化状态文件，例如 `active_instance.json`：

```json
{
  "instance_id": "eva-20260415-001",
  "generation": 12,
  "lease_expires_at": "2026-04-15T12:00:15Z"
}
```

当前实例自身同时持有：
- 自己的 `instance_id`
- 自己的 `generation`
- 自己是否仍持有 lock

在每次 tick / turn 中读取并比对，从而得到内部可读的 `instance_valid`。

### 8.13 当 `instance_valid=false` 时的本体行为
第一版采用硬约束：
- 不再执行普通 turn
- 只允许写一次状态
- 只允许发出 distress / yield 信号
- 停止普通任务
- 退出或等待 supervisor 接管

含义：

**一旦不再被承认为合法执行者，就不再代表 eva 行动。**

### 8.14 Step 0 的最小运行壳边界
Step 0 的最小运行壳只承载“让 eva 成为可持续存在的运行体”所必需的组件，不提前承载更高层能力。

第一版**必须包含**：

#### A. supervisor 配合层
- 由宿主环境负责进程守护与异常退出后重启
- 负责把 Python 运行壳作为长期后台进程拉起
- 这一层先不放进 eva 本体逻辑里

#### B. 单实例合法性层
- lock 文件
- active instance 状态文件
- generation 递增与比对
- lease 刷新与过期判断

#### C. 事件驱动主循环层
- heartbeat deadline 调度
- 外部 / 时间 / 内源信号进入主循环
- tick 与 turn 的分流

#### D. 基础 heartbeat 层
- 15 秒基础 heartbeat
- tick_id / wake_reason 记录
- 生命体征采样
- 内部生命函数判断
- heartbeat 与状态快照落盘

#### E. turn 执行层
- 读取触发来源
- 判断 heartbeat deadline
- 读取 `life_state` 与 `instance_valid`
- 选取并执行一个可续接的 work slice
- 落盘结果并返回主循环

#### F. 状态持久化层
- `active_instance.json`：当前活跃实例投影
- `runtime_state.json`：当前 life_state、最近 heartbeat、失败计数等
- `events.log` 或等价事件日志：记录 tick / turn / error / yield

#### G. 最小 distress / yield 机制
- 当进入 `CRITICAL` 或 `instance_valid=false` 时
- 至少能落盘一条 distress / yield 事件
- 第一版不要求复杂通知系统，只要求本地可观察与可追溯

第一版**明确不包含**：
- LLM 调用
- 多工具系统
- 长链路任务编排
- 复杂任务队列
- 复杂记忆检索
- skill 自动生成
- 多渠道消息网关
- 经济系统
- LoRA / 蒸馏
- 多机分布式一致性

### 8.15 Step 0 的最小文件布局建议
第一版建议先收敛到极少文件：

```text
eva-agent/
  README.md
  CLAUDE.md
  docs/
    project-definition.md
    step-0-life-loop.md
  eva/
    main.py           # 主入口 / 事件驱动主循环
    lifecycle.py      # tick / turn / life_state 逻辑
    instance.py       # lock / generation / lease / instance_valid
    state.py          # runtime_state / active_instance / event log 持久化
    config.py         # heartbeat / 路径 / 阈值配置
```

说明：
- `main.py` 只负责启动运行壳和进入主循环
- `lifecycle.py` 承接 tick / turn 两种最小序列
- `instance.py` 承接合法性投影机制
- `state.py` 承接最小持久化
- `config.py` 集中阈值与路径，便于后续调参

### 8.16 Step 0 的完成判据
当最小运行壳具备以下能力时，Step 0 可以视为完成：
- supervisor 能把进程长期拉起
- 基础 heartbeat 能按 15 秒节律持续写出
- tick / turn 能按已定义边界分开运行
- `instance_valid` 能在单机前提下正确投影合法执行身份
- 状态、错误和 distress / yield 事件能持续落盘
- 普通任务不会长期阻塞 heartbeat

### 8.17 当前已完成的第一轮实现
当前已经完成第一轮 Step 0 落地：
- 已新增实现合同文档、持久化协议、验证方案与 Linux 部署示例
- 已新增 `eva/config.py`、`eva/state.py`、`eva/instance.py`、`eva/lifecycle.py`、`eva/main.py`
- 已支持 bounded run，可在 mac 本地用临时 runtime 目录进行快速验证
- 已完成 `tests/test_state.py`、`tests/test_instance.py`、`tests/test_lifecycle.py`、`tests/test_main_loop.py`
- 当前已通过 mac 本地单测与 bounded smoke test
- 已在远程 Ubuntu 24.04 主机上用 `systemctl --user` 成功部署到隔离目录 `~/apps/eva-agent`
- 已验证 runtime 文件生成、service 启动、手动 restart 后 generation 递增与实例接管
- 更长时间运行观察、异常注入与日志可观测性仍待继续补强

## 9. Step 0 当前未定项
当前仍待继续讨论：
1. 在 Linux 长期在线环境完成更长时间验证后，何时从 Step 0 进入 Step 1（也就是 first patrol 层何时长出）
