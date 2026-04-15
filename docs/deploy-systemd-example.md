# Linux 部署示例（Step 0）

## 1. 目的
这份文档只提供 Step 0 最小运行壳在 Linux 上的部署示例。

它的作用是：
- 验证长期在线环境是否能稳定承载基础 heartbeat
- 把 supervisor 职责留给宿主环境
- 不把 systemd 逻辑写进 eva 本体代码

## 2. 为什么可以先在 mac 开发
Step 0 的大部分实现与测试可以先在 mac 本地完成，因为：
- 状态机逻辑与 JSON 持久化平台无关
- `fcntl` 文件锁在 mac / Linux 都可用
- bounded run 能覆盖大多数开发期问题

但 Linux 仍是最终目标环境，因为：
- 真实长期运行要依赖 Linux 守护能力
- systemd 是首版 supervisor 配合层的主要假设
- 目标路径权限、用户、工作目录和后台运行行为需要在 Linux 复核

## 3. 推荐目录
首版优先采用**用户级隔离部署**，避免影响机器上已有服务：

```text
~/apps/eva-agent/                      # 代码目录
~/.local/state/eva-agent/runtime/     # runtime 数据
~/.config/systemd/user/               # user systemd unit
```

只有在后续需要更强隔离或 root 级服务管理时，才再切到 `/opt`、`/var/lib` 这类系统目录。

## 4. user systemd unit 示例
```ini
[Unit]
Description=eva-agent Step 0 runtime
After=default.target

[Service]
Type=simple
WorkingDirectory=%h/apps/eva-agent
ExecStart=/usr/bin/python3 -m eva.main --runtime-dir %h/.local/state/eva-agent/runtime
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```

## 5. 当前远程机器的推荐部署步骤
已确认远程机器具备：
- Ubuntu 24.04 / Python 3.12
- `systemctl --user` 可用
- `loginctl show-user test -p Linger` 返回 `Linger=yes`
- 机器已有其他用户级服务，因此**不需要全新干净环境**，但应采用独立目录与独立 service 名称

### 5.1 上传代码
推荐把当前项目同步到：

```bash
~/apps/eva-agent/
```

### 5.2 创建目录
```bash
mkdir -p ~/apps/eva-agent
mkdir -p ~/.local/state/eva-agent/runtime
mkdir -p ~/.config/systemd/user
```

### 5.3 安装 user service
项目内已提供：
- `deploy/systemd/user/eva-agent.service`
- `deploy/install-user-service.sh`

在项目根目录执行：

```bash
bash deploy/install-user-service.sh
```

它会把 service 复制到：

```bash
~/.config/systemd/user/eva-agent.service
```

然后执行：

```bash
systemctl --user daemon-reload
systemctl --user enable --now eva-agent.service
systemctl --user status eva-agent.service --no-pager
```

### 5.4 基本验证命令
```bash
systemctl --user status eva-agent.service --no-pager
journalctl --user -u eva-agent.service -n 50 --no-pager
ls -la ~/.local/state/eva-agent/runtime
python3 - <<'PY'
import json
from pathlib import Path
runtime = Path.home() / '.local/state/eva-agent/runtime'
for name in ['active_instance.json', 'runtime_state.json', 'events.jsonl']:
    path = runtime / name
    print(name, path.exists(), path)
if (runtime / 'runtime_state.json').exists():
    print(json.loads((runtime / 'runtime_state.json').read_text(encoding='utf-8')))
PY
```

### 5.5 异常注入验证命令
#### generation mismatch
```bash
python3 - <<'PY'
import json
from pathlib import Path
runtime = Path.home() / '.local/state/eva-agent/runtime'
path = runtime / 'active_instance.json'
data = json.loads(path.read_text(encoding='utf-8'))
data['generation'] = data['generation'] + 100
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(data)
PY
sleep 18
journalctl --user -u eva-agent.service -n 20 --no-pager
cat ~/.local/state/eva-agent/runtime/runtime_state.json
```

#### lease 过期 + recovery
```bash
systemctl --user stop eva-agent.service
sleep 22
cat ~/.local/state/eva-agent/runtime/active_instance.json
systemctl --user start eva-agent.service
sleep 3
systemctl --user status eva-agent.service --no-pager
cat ~/.local/state/eva-agent/runtime/active_instance.json
```

#### distress 注入
```bash
python3 - <<'PY'
from pathlib import Path
import json
path = Path.home() / '.local/state/eva-agent/runtime/distress_injection.json'
path.write_text(json.dumps({'reason': 'manual_distress_test'}, ensure_ascii=False) + '\n', encoding='utf-8')
print(path)
PY
sleep 18
journalctl --user -u eva-agent.service -n 20 --no-pager
python3 - <<'PY'
import json
from pathlib import Path
runtime = Path.home() / '.local/state/eva-agent/runtime'
print('injection_exists', (runtime / 'distress_injection.json').exists())
lines = (runtime / 'events.jsonl').read_text(encoding='utf-8').splitlines()
for line in lines[-12:]:
    if line.strip():
        print(json.loads(line))
PY
```

预期：
- 下一次 heartbeat 进入 `CRITICAL`
- journal 出现 `event=distress reason=manual_distress_test`
- `events.jsonl` 追加 `event_type=distress`
- `distress_injection.json` 被一次性消费后删除
- 再下一次 heartbeat 恢复到 `STABLE`

如需回滚：

```bash
systemctl --user disable --now eva-agent.service
rm -f ~/.config/systemd/user/eva-agent.service
systemctl --user daemon-reload
```

是否删除运行数据再另行决定，默认保留：

```bash
~/.local/state/eva-agent/runtime
```

## 6. Linux 验证重点
启动后检查：
- `~/.local/state/eva-agent/runtime/active_instance.json` 是否生成
- `~/.local/state/eva-agent/runtime/runtime_state.json` 是否持续刷新
- `~/.local/state/eva-agent/runtime/events.jsonl` 是否持续追加 heartbeat 相关事件
- `systemctl --user status eva-agent.service` 是否为 `active (running)`
- `journalctl --user -u eva-agent.service` 是否无持续崩溃重启

## 7. 当前限制
Step 0 还不包含：
- 多实例协调
- 分布式一致性
- 外部监控告警
- Step 1 巡逻任务

所以这份部署示例只用于验证：
- 最小运行壳能否在 Linux 上长期活着
- supervisor 与本体边界是否清晰
