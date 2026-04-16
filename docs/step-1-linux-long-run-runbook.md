# Step 1 Linux Long-Run Observation Runbook

## Purpose
This runbook is the minimal procedure for running `eva-agent` Step 1 on the Linux target host with real cadence values and checking whether the 24-hour observation meets expectations.

It is intended to confirm that Step 1 is not only correct under local and accelerated verification, but also stable under real long-running Linux execution.

## Target cadence
Use the real Step 1 cadence values:
- heartbeat: 15 seconds
- shallow patrol: 5 minutes
- deep patrol: 30 minutes
- full report: 24 hours
- recent event window: 30 minutes

## Preconditions
Before starting the 24-hour observation, confirm:
- the code under `~/apps/eva-agent/` is the intended Step 1 version
- `systemctl --user` is available
- the service is installed as `eva-agent.service`
- the runtime path is `~/.local/state/eva-agent/runtime`
- the host user has linger enabled if required for long-running user services

## Service definition
The user service should run `eva.main` with explicit real cadence values.

Expected command:

```bash
/usr/bin/python3 -m eva.main \
  --runtime-dir %h/.local/state/eva-agent/runtime \
  --heartbeat-interval 15 \
  --lease-duration 20 \
  --recovering-window 30 \
  --turn-guard-window 0.5 \
  --idle-sleep-sec 0.05 \
  --shallow-patrol-interval 300 \
  --deep-patrol-interval 1800 \
  --full-report-interval 86400 \
  --recent-event-window 1800
```

## Deployment steps
From the local project root:

```bash
rsync -az --exclude '.git/' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.mypy_cache/' --exclude '.DS_Store' ./ 100.111.17.101:~/apps/eva-agent/
ssh 100.111.17.101 'cd ~/apps/eva-agent && bash deploy/install-user-service.sh'
```

Then confirm the service picked up the intended unit:

```bash
ssh 100.111.17.101 'systemctl --user cat eva-agent.service'
```

## Start or restart the observation
Apply the updated unit and restart the user service:

```bash
ssh 100.111.17.101 '
  systemctl --user daemon-reload &&
  systemctl --user restart eva-agent.service &&
  systemctl --user status eva-agent.service --no-pager
'
```

## Start-time checks
Immediately after restart, verify:

```bash
ssh 100.111.17.101 '
  journalctl --user -u eva-agent.service -n 60 --no-pager &&
  ls -la ~/.local/state/eva-agent/runtime
'
```

Expected at start:
- service is `active (running)`
- `runtime_state.json` continues updating
- `events.jsonl` continues appending
- Step 1 files exist or begin to appear:
  - `external_life_snapshot.json`
  - `active_pressures.json`
  - `survival_log.jsonl`

## Observation window
Let the service continue running for at least 24 hours.

During the window, do not replace the runtime directory unless recovery testing is intentional.
If you need spot checks, use read-only inspection commands.

## Spot-check commands during the run
Check service and latest journal:

```bash
ssh 100.111.17.101 '
  systemctl --user status eva-agent.service --no-pager &&
  journalctl --user -u eva-agent.service -n 120 --no-pager
'
```

Check current runtime artifacts:

```bash
ssh 100.111.17.101 'python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path
runtime = Path.home() / ".local/state/eva-agent/runtime"
for name in [
    "runtime_state.json",
    "external_life_snapshot.json",
    "active_pressures.json",
    "survival_log.jsonl",
    "events.jsonl",
]:
    path = runtime / name
    print(f"--- {name} exists={path.exists()} ---")
    if not path.exists():
        continue
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if name == "runtime_state.json":
            print("life_state", data.get("life_state"), "instance_valid", data.get("instance_valid"))
        elif name == "external_life_snapshot.json":
            print("source_patrol", data.get("source_patrol"), "overall_status", data.get("overall_status"), "trend", data.get("trend"))
        elif name == "active_pressures.json":
            print("pressure_count", len(data.get("pressures", [])))
    else:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print("line_count", len(lines))
PY'
```

## 24-hour completion check
After the observation window, verify:

### 1. Service stayed alive
- `systemctl --user status eva-agent.service` is still `active (running)`
- journal does not show crash loops or repeated restart churn

### 2. Heartbeat-first behavior still held
- journal shows regular `event=tick`
- there is no sign that patrol execution suppressed heartbeat updates

### 3. Step 1 files were continuously produced
These files should exist and remain readable:
- `external_life_snapshot.json`
- `active_pressures.json`
- `survival_log.jsonl`

### 4. Real cadence patrols actually appeared
Across journal and/or `events.jsonl`, confirm that:
- `shallow` occurred
- `deep` occurred
- `full` occurred

For the first true 24-hour validation, the critical point is that at least one real `full` patrol or full report has appeared under the 24-hour cadence.

### 5. History and current state are consistent
- `external_life_snapshot.json` reflects the latest current state
- `active_pressures.json` reflects currently active pressures only
- `survival_log.jsonl` contains append-only history entries such as:
  - `survival_snapshot`
  - `pressure_opened`
  - `pressure_resolved` if an observed issue recovered

## Recommended final inspection command
```bash
ssh 100.111.17.101 'python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path
from collections import Counter
runtime = Path.home() / ".local/state/eva-agent/runtime"
print("runtime", runtime)
snapshot = json.loads((runtime / "external_life_snapshot.json").read_text(encoding="utf-8"))
pressures = json.loads((runtime / "active_pressures.json").read_text(encoding="utf-8"))
survival = [json.loads(line) for line in (runtime / "survival_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
events = [json.loads(line) for line in (runtime / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
patrol_turns = [event for event in events if event.get("event_type") == "turn_completed" and event.get("details", {}).get("work_kind") == "patrol"]
print("snapshot_source", snapshot.get("source_patrol"))
print("overall_status", snapshot.get("overall_status"))
print("trend", snapshot.get("trend"))
print("primary_gap", snapshot.get("primary_gap"))
print("pressure_count", len(pressures.get("pressures", [])))
print("survival_event_counts", dict(Counter(item.get("event_type") for item in survival)))
print("patrol_turn_count", len(patrol_turns))
print("patrol_cadences_seen", sorted(set(item.get("details", {}).get("cadence") for item in patrol_turns if item.get("details", {}).get("cadence"))))
PY'
```

## Success criteria
The 24-hour observation can be considered successful if:
1. the service stayed active throughout the window
2. heartbeat updates remained stable
3. Step 1 current-state files stayed readable and updated
4. `survival_log.jsonl` kept appending normally
5. real `shallow`, `deep`, and `full` patrols were observed
6. no evidence showed patrol work breaking the heartbeat-first lifecycle boundary

## Rollback
If the run must be stopped:

```bash
ssh 100.111.17.101 'systemctl --user stop eva-agent.service'
```

If the unit must be removed:

```bash
ssh 100.111.17.101 '
  systemctl --user disable --now eva-agent.service || true &&
  rm -f ~/.config/systemd/user/eva-agent.service &&
  systemctl --user daemon-reload
'
```

Runtime data is kept by default at:

```text
~/.local/state/eva-agent/runtime
```
