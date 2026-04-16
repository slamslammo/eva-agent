# Step 1 验证方案

## 1. 目标
验证 Step 1 是否已经从“只有心脏在跳”的最小生命循环，推进到“开始形成外部生命函数”的第一轮实现。

这一轮验证的重点不是“能不能做复杂行动”，而是确认以下四类能力是否真实长出：
- 外部生命感知
- 规则式生命判断
- 生存压力生成
- 最小历史记录

同时必须继续证明：
- Step 0 的 heartbeat-first 生命循环没有被破坏
- `tick / turn` 的边界没有被 Step 1 污染
- Step 1 的派生状态与历史记录真实产出、真实可追溯

换句话说：

> Step 1 的验证，不只是验证“巡逻有没有跑”，而是验证“巡逻是否真的产出了外部生命快照、生命判断、active pressure 与最小生存历史”。

---

## 2. 验证分层
### A. Step 0 非回归验证
验证 Step 1 引入后，Step 0 的基础生命循环语义仍然成立。

### B. Step 1 单元测试
验证 Step 1 新增长出的感知、判断、压力与历史记录模块边界。

### C. accelerated cadence 本地集成验证
用缩短后的 shallow / deep / full 节律，在本地有限时间内验证 Step 1 端到端产物。

### D. Linux 长时运行验证
在长期在线 Linux 环境中验证：
- 巡逻长期稳定运行
- Step 1 新文件持续更新
- pressure 的开启 / 关闭能留下可追溯历史
- heartbeat 优先级未被破坏

---

## 3. Step 0 非回归验证
Step 1 上线前后，必须继续保留并跑通 Step 0 的既有测试。

### 必须保持不变的语义
1. heartbeat 仍优先于普通 turn
2. `turn` 在 heartbeat deadline 临近时仍然让位
3. `instance_valid=false` 时不再继续执行普通工作
4. `CRITICAL` 状态下不执行普通 Step 1 巡逻逻辑
5. bounded run 仍可稳定退出
6. `active_instance.json` / `runtime_state.json` / `events.jsonl` 的 Step 0 含义不变

### 对应测试
- `tests/test_state.py`
- `tests/test_instance.py`
- `tests/test_lifecycle.py`
- `tests/test_main_loop.py`

### 验证重点
- `runtime_state.json` 中不应混入 Step 1 snapshot / pressure 字段
- `turn_completed` / `yield` / `distress` 等核心事件语义保持兼容
- Step 1 新逻辑不能让 `tick` 变成长路径

---

## 4. Step 1 单元测试清单
Step 1 第一轮建议新增或扩展以下测试。

### 4.1 `tests/test_sensing.py`
覆盖：
- 宿主连续性采样
- runtime 路径存在性与可写性检查
- 基础资源状态采样
- 从现有 Step 0 事件窗口中提取本地异常积累信号

验证点：
- 输入固定条件时，感知输出稳定且可重复
- 第一轮只覆盖宿主 / 本地 / runtime 层，不触发网络 / API 依赖

### 4.2 `tests/test_judgment.py`
覆盖：
- 单维度状态判断：`healthy / degraded / critical`
- 多维度收敛为整体外部生命状态
- 主缺口识别
- 趋势判断：`improving / stable / worsening / unknown`

验证点：
- 相同输入应得到相同判断结果
- 判断逻辑保持规则式、稳态导向，不依赖 LLM 或开放式推理

### 4.3 `tests/test_pressure.py`
覆盖：
- continuity / resource_state / integrity / anomaly_accumulation 四类压力生成
- 压力严重级别计算
- `pressure_id` 稳定性
- 压力 active / resolved 判定

验证点：
- 同一类问题跨次巡逻应被识别为同一压力
- 压力变化应可区分“新开”“持续存在”“已解除”
- 压力不直接退化成任务对象

### 4.4 `tests/test_history.py`
覆盖：
- 写入 `external_life_snapshot.json`
- 写入 `active_pressures.json`
- 追加 `survival_log.jsonl`
- `pressure_opened / pressure_resolved / survival_snapshot` 的历史写入

验证点：
- 当前态文件覆盖写不应破坏历史日志
- 生存日志单条记录必须自包含
- Step 1 三个文件可单独读取理解

### 4.5 `tests/test_patrol.py`
覆盖：
- shallow / deep / full patrol 的 due 判断
- 同一 due 巡逻不会重复 enqueue
- multiple due 时按固定顺序调度
- patrol 结果驱动 Step 1 文件更新

建议顺序：
- `shallow -> deep -> full`

---

## 5. accelerated cadence 本地集成验证
由于真实节律是：
- shallow：5 分钟
- deep：30 分钟
- full：24 小时

本地开发阶段不能按真实时间等待，因此需要 accelerated cadence 验证。

### 5.1 目标
在有限时间内确认：
- shallow / deep / full 三层巡逻都能真实触发
- 巡逻结果能更新 Step 1 三个文件
- pressure 的开启 / 关闭能留下历史
- heartbeat 仍然优先

### 5.2 建议做法
在本地测试配置里把节律缩短，例如：
- shallow：5 秒
- deep：15 秒
- full：30 秒

再运行 bounded runtime，观察多个 patrol 周期。

### 5.3 预期验证点
1. runtime 目录新增：
   - `external_life_snapshot.json`
   - `active_pressures.json`
   - `survival_log.jsonl`

2. `external_life_snapshot.json` 可看到：
   - 维度级判断
   - 整体外部生命状态
   - 当前主缺口
   - 趋势

3. `active_pressures.json` 可看到：
   - 当前 active pressure
   - 稳定 `pressure_id`
   - severity / evidence / trend

4. `survival_log.jsonl` 可看到：
   - `survival_snapshot`
   - `pressure_opened`
   - `pressure_resolved`（如果在测试窗口内出现）

5. bounded run 结束后：
   - `tick` 仍按预期节律发生
   - `turn` 没有压住 heartbeat

---

## 6. 行为路径验证
### 6.1 正常路径
方式：
- 在正常 runtime 目录、可写磁盘、稳定 heartbeat 条件下运行 accelerated cadence

预期：
- `external_life_snapshot.json` 中大部分维度为 `healthy`
- `active_pressures.json` 为空或只有低级 pressure
- `survival_log.jsonl` 可连续追加 `survival_snapshot`

### 6.2 资源压力路径
方式：
- 注入低磁盘空间阈值或不可写 runtime 条件（测试替身 / 临时目录权限控制）

预期：
- 形成 `resource_state` 压力
- `external_life_snapshot.json` 中 `resource_state.status=degraded/critical`
- `active_pressures.json` 出现对应 pressure
- `survival_log.jsonl` 追加 `pressure_opened`

### 6.3 完整性压力路径
方式：
- 注入状态文件不一致、写入中断或关键文件异常条件

预期：
- 形成 `integrity` 压力
- 快照中整体外部生命状态进入 `degraded` 或 `critical`
- 生存日志留下阶段性外部生命判断记录

### 6.4 异常积累路径
方式：
- 在测试窗口内注入多次 `yield` / `distress` / restart 类信号

预期：
- 形成 `anomaly_accumulation` 压力
- 趋势判断从 `stable` 转向 `worsening`
- `survival_log.jsonl` 中可看到压力开启与持续存在

### 6.5 压力解除路径
方式：
- 在前一次巡逻制造压力，再恢复正常环境继续运行

预期：
- `active_pressures.json` 中对应压力消失
- `survival_log.jsonl` 追加 `pressure_resolved`
- 快照整体状态恢复到 `healthy` 或 `stable`

---

## 7. 巡逻与 heartbeat 关系验证
这是 Step 1 最关键的非功能验证之一。

### 必须成立的约束
1. patrol 只能通过 `turn` work slice 执行
2. patrol 不能进入 `tick`
3. heartbeat deadline 临近时，patrol 必须让位
4. Step 1 新逻辑不能让 `tick` 变成长路径

### 验证方式
- 复用 `tests/test_lifecycle.py` 中 turn 让位的测试思路
- 新增 patrol due 时的让位场景
- 在 accelerated cadence 下观察：即使 patrol 连续 due，heartbeat 仍按节律运行

### 预期
- patrol due ≠ 立即执行成功
- 若 heartbeat deadline 近，`turn` 仍返回让位
- `events.jsonl` 中继续能观察到清晰的 tick 节律

---

## 8. Step 1 文件边界验证
### 8.1 当前态文件
验证：
- `external_life_snapshot.json` 只保存当前快照
- `active_pressures.json` 只保存当前 active 压力

预期：
- 新一轮覆盖写后，文件仍保持自解释
- 不保存无穷累积历史

### 8.2 历史文件
验证：
- `survival_log.jsonl` 只做追加
- 单条记录不依赖上下文即可理解

预期：
- `survival_snapshot` 与 `pressure_opened / pressure_resolved` 顺序合理
- 历史变化可回放

### 8.3 Step 0 文件未被污染
验证：
- `runtime_state.json` 仍只承载 Step 0 生命状态
- `events.jsonl` 仍是原始运行事件主记录

预期：
- Step 1 的派生状态不进入 Step 0 基础状态文件

---

## 9. mac 与 Linux 的验证分工
### 9.1 mac 本地
适合：
- Step 1 单元测试
- accelerated cadence 本地集成验证
- 当前态文件与历史文件写入验证
- heartbeat 与 patrol 让位关系验证

不应视为最终完成的内容：
- 长期 systemd 托管验证
- 长时运行下 pressure 历史稳定性
- Linux 权限、工作目录与 crash recovery 细节

### 9.2 Linux 目标环境
必须补：
- Step 1 新文件在真实 runtime 路径下持续生成与更新
- user systemd 长时运行下 shallow / deep / full 都真实出现
- `survival_log.jsonl` 长时追加正常
- active pressure 在真实异常注入后能打开 / 解除
- journal 中能看到 Step 0 基础事件与 Step 1 patrol 相关日志

---

## 10. Linux 长时运行验证
### 10.1 最小验证目标
在远程 Linux 环境中至少验证：
1. shallow / deep / full 三层巡逻都能按节律真实触发
2. `external_life_snapshot.json` 持续刷新
3. `active_pressures.json` 在异常出现 / 解除时正确变化
4. `survival_log.jsonl` 连续追加
5. heartbeat 仍保持稳定，不被 patrol 压住

### 10.2 建议验证窗口
第一轮建议至少覆盖：
- 一轮 accelerated long-run（便于快速校验）
- 一轮更接近真实节律的连续观察

### 10.3 关键观察项
- 有没有跳过应有的 patrol
- 有无 patrol 重复入队
- `pressure_id` 是否稳定
- Step 1 当前态文件与历史文件是否一致
- stress 条件解除后 pressure 是否能 resolved

---

## 11. 完成标准
可以宣称 Step 1 第一轮 docs-first 之后的实现完成时，应满足：

1. Step 0 现有测试全绿
2. Step 1 新增单元测试全绿
3. accelerated cadence 本地集成验证全绿
4. 运行后真实生成：
   - `external_life_snapshot.json`
   - `active_pressures.json`
   - `survival_log.jsonl`
5. 至少成功覆盖一次：
   - pressure_opened
   - pressure_resolved
6. Linux 上完成一轮长时运行补验证
7. 整个过程中 heartbeat-first 的生命循环语义保持成立

---

## 12. 一句话收口

> Step 1 的验证，不是验证“巡逻有没有存在”，而是验证 eva 是否已经开始持续产出外部生命快照、结构化生存压力和最小生存历史，同时仍保持 Step 0 的生命循环边界不被破坏。
