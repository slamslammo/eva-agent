# Step 0 验证方案

## 1. 目标
验证 Step 0 是否已经成为一个最小但真实的“生命体”运行壳，而不是一组静态定义。

## 2. 验证分层
### A. 单元测试
验证最小模块边界：
- state 持久化
- instance 合法性投影
- lifecycle 状态转换
- bounded main loop

### B. bounded smoke test
在临时 runtime 目录运行有限轮次主循环，验证文件与事件是否真实产出。

### C. Linux 补充验证
在长期在线 Linux 环境验证部署、锁、路径和长期运行稳定性。

当前首选验证方式：
- 上传到 `~/apps/eva-agent`
- 使用 `systemctl --user` 运行 `eva-agent.service`
- runtime 放在 `~/.local/state/eva-agent/runtime`
- 不影响机器已有其他服务

## 3. 自动化测试清单
### `tests/test_state.py`
覆盖：
- 初始化 runtime 目录
- 读写 `runtime_state.json`
- 读写 `active_instance.json`
- 追加 `events.jsonl`
- 状态文件原子写入后仍可读

### `tests/test_instance.py`
覆盖：
- 获取 lock 成功
- 同一路径第二实例获取 lock 失败
- generation 递增
- lease 刷新
- `instance_valid` 在 lock 丢失 / generation 不匹配 / lease 过期时变为 false

### `tests/test_lifecycle.py`
覆盖：
- `RECOVERING -> STABLE`
- heartbeat 过期进入 `DEGRADED`
- 连续失败或关键条件进入 `CRITICAL`
- `turn` 在 heartbeat deadline 临近时让位
- `CRITICAL` 或 `instance_valid=false` 时普通 turn 不执行

### `tests/test_main_loop.py`
覆盖：
- bounded run 能正常退出
- 运行后生成 `active_instance.json`、`runtime_state.json`、`events.jsonl`
- 启动、tick、turn、shutdown 事件存在
- 注入失效条件后只剩 distress / yield 路径

## 4. CLI 烟雾测试
建议支持如下命令：

```bash
python -m eva.main --runtime-dir /tmp/eva-runtime --max-ticks 3 --max-turns 2
```

验证点：
- 命令退出码为 0
- 输出包含最终摘要
- runtime 目录生成 3 个核心文件
- `events.jsonl` 至少包含 `startup`、`tick_completed`、`shutdown`

## 5. 异常路径验证
### 5.1 lease 过期
方式：
- 用测试配置把 lease 设置得很短
- 人工推进时钟或显式注入过期时间
- Linux 上也可通过 `systemctl --user stop eva-agent.service` 后等待 lease 超时来验证

预期：
- `instance_valid=false`
- 普通 turn 停止
- 追加 `yield` 事件
- journal 中出现明确的 `event=yield` 或后续 restart 的 `event=startup`

### 5.2 generation 不匹配
方式：
- 篡改 `active_instance.json` 的 generation

预期：
- 当前实例识别为旧代
- 不再执行普通 turn
- 写出 `yield`

### 5.3 lock 丢失
方式：
- 在测试替身或显式释放锁后再次检查合法性

预期：
- `instance_valid=false`
- 不再继续普通任务路径

### 5.4 heartbeat 连续失败 / distress 注入
方式：
- 本地单测中写入 `distress_injection.json`，由下一次 tick 一次性消费
- Linux 上可在 `~/.local/state/eva-agent/runtime/distress_injection.json` 写入 `{"reason":"manual_distress_test"}`
- 也可继续通过状态写入失败或生命体征采样失败推进真实 heartbeat failure 路径

预期：
- 注入文件会在消费后被删除，避免重复触发
- 当前实例仍保持 `instance_valid=true`
- `life_state` 进入 `CRITICAL`
- journal 中出现 `event=distress reason=manual_distress_test`
- `events.jsonl` 写出 `event_type=distress`，且 `details.source=distress_injection_file`

## 6. mac 与 Linux 的验证分工
### mac 本地
适合：
- 日常开发
- 单元测试
- bounded smoke test
- 基础文件锁与状态机测试
- stdout 结构化日志格式验证

不应把以下结果视为最终完成：
- systemd 启动验证
- 真实长期后台运行验证
- Linux 权限与工作目录行为

### Linux 目标环境
必须补：
- `python -m eva.main` 在真实 runtime 路径下运行
- user systemd unit 启动、重启与工作目录
- 长时间 heartbeat 与 lease 刷新
- 异常退出后的 user systemd 重拉起
- 在与其他已有部署共存时，目录和 service 名称不冲突
- journal 中能直接看到 `startup` / `tick` / `transition` / `yield` / `distress` / `shutdown`

### 当前已完成的 Linux 实测
已在远程 Ubuntu 24.04 主机上完成：
- user systemd 隔离部署
- 连续多轮 heartbeat 观察，`life_state=STABLE`
- generation mismatch 注入：进入 `CRITICAL`，并写出 `event=yield reason=generation_mismatch`
- service stop 后等待 lease 过期，再 start：成功生成新实例并递增 generation
- `distress_injection.json` 注入：下一次 heartbeat 进入 `CRITICAL`，写出 `event=distress reason=manual_distress_test`，注入文件被消费删除，随后恢复 `STABLE`

## 7. 完成标准
可以宣称 Step 0 第一轮实现完成时，应满足：
- 单测全绿
- bounded smoke test 全绿
- 异常路径至少覆盖 lease 过期 / generation 不匹配 / heartbeat 失败
- Linux 上完成一轮最小部署验证
