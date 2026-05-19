# Round 1.B-4 — Signal Classification De-coupling — Startup Instruction

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.B-4 — fix signal class semantics; Linux-residue 第 7 处，Round 1.B-1 漏扫的

**Companion documents**:
- `.claude/plans/federated-snacking-engelbart.md`
- `maintainer/development/round-1b-1-progress.md` — 历史上扫了 reasoning 层 Linux 残留，没扫 signal 分类层
- Phase-1.5 经验数据：`validation-runs/phase1-10min/` 显示 threat_present=200/200，但其中实际是 acquisition/capability 假"威胁"

---

## 1. 问题

`eva/l1_sensing/signal_bus.py:71-72`：

```python
for pressure in pressure_table.pressures:
    signals.append(build_threat_signal(snapshot, pressure))
```

**所有 pressure 都被打成 `class="threat"`**——不管它是 safety（真威胁）还是 metabolic / acquisition / capability / recovery（慢性压力）。

下游 6 处消费了这个错误等价：

| # | 位置 | 受害 |
|---|---|---|
| A | `routing.py:39` `has_threat_signal` | Crafter 每 tick urgency=high |
| B | `routing.py:68-79` `_has_critical_integrity_threat` | 硬编码 type=="integrity" — **Round 1.B-1 漏扫的** |
| C | `drive_state.py:181` `threat_present` 检测 | exploration drive 永远被压 |
| D | `value_judgment.py:18` `threat_count` 进 score | capability/acquisition 压力被加 score_delta |
| E | `encoding.py:115-117` memory salience | 看见树都被记作 high salience |
| F | `reflex.py` | 间接受 routing 决定影响 |

v0.5 Linux 时代 pressure 几乎都是 integrity 类，"all pressure → threat" 没问题。v0.6 引入 5 类 Crafter pressure 后，本来就该改，Round 1.B-1 没扫到 signal 分类层。

---

## 2. 目标语义

**修正后**：
- `class="threat"` = **imminent threat**（真危险，需要紧急响应、压制 exploration、加 memory salience）
- `class="pressure"` = **active pressure but not imminent**（慢性压力，影响 drive level / candidate scoring，但不触发威胁响应语义）
- `class="status"` / `class="background"` 不变

**scenario-driven 配置**：scenario bundle 声明哪些 pressure type 算 imminent。
- Linux：`imminent_threat_pressure_types = ("integrity",)`
- Crafter：`imminent_threat_pressure_types = ("safety",)`
- 默认：`()`（保守：不算 imminent，除非 scenario 明确声明）

---

## 3. Scope

### 修改文件（framework）
- `eva/scenario_bundle.py` — `SensorPolicyBundle` 加 `imminent_threat_pressure_types`
- `eva/l1_sensing/signal_bus.py` — `build_threat_signal` 分流；`SignalDispatchSummary` 加 `pressure_signal_count` 便于调试
- `eva/l1_sensing/routing.py` — `_has_critical_integrity_threat` 改成 scenario-driven（同时去掉硬编码 type=="integrity"）
- `eva/l3_deliberation/reasoning/value_judgment.py` — threat_count 注释/语义同步
- `eva/l3_deliberation/memory/encoding.py` — salience 计算同步
- `eva/l2_drive/reflex.py` — 检查是否需要同步

### 修改文件（scenario）
- `scenarios/linux_runtime/__init__.py` 或 sensor 配置位置 — 声明 `imminent_threat_pressure_types=("integrity",)`
- `scenarios/crafter/__init__.py` 同 — 声明 `imminent_threat_pressure_types=("safety",)`

### 测试
- 新增 `tests/l1_sensing/test_signal_classification.py`：失败测试 pin 新语义
- 更新现有测试中断言 `threat_signal_count` 包含 acquisition/capability 类的——这些是错的，要改成符合新语义

---

## 4. 实施 slice

### 1.B-4-a：失败测试 + scenario 配置项
- 新增 SensorPolicyBundle 字段 `imminent_threat_pressure_types: tuple[str, ...] = ()`
- 写失败测试：Crafter scenario 激活后 acquisition pressure 应产生 class="pressure"，safety pressure 应产生 class="threat"

### 1.B-4-b：build_threat_signal 分流
- 改 `build_threat_signal` 根据 pressure.type 是否在配置中决定 class
- 新增 `SignalDispatchSummary.pressure_signal_count`
- 更新 `summarize_signal_dispatch`

### 1.B-4-c：下游消费者同步
- `routing.py`：`_has_critical_integrity_threat` 拆开（去硬编码 integrity）
- `drive_state.py`：threat_present 检测保持 `class=="threat"` 即可（语义已对）
- `value_judgment.py`：threat_count 注释更新（语义改变但代码不需要改——它一直读 summary）
- `encoding.py`：同上
- `reflex.py`：fast-path 触发条件可能需要更新

### 1.B-4-d：scenario 声明 imminent types
- Linux 声明 ("integrity",)
- Crafter 声明 ("safety",)

### 1.B-4-e：回归 + Crafter 3min smoke 验证 exploration drive 真起来

---

## 5. 边界

**必须保持**：
- Linux 行为 bit-equivalent（imminent_threat 列表设 integrity，效果与硬编码 type=="integrity" 等价）
- mediator / anchor / release token / heartbeat / instance legitimacy 全部不动
- 现有 trace schema 兼容（class="pressure" 是新增枚举值，老 trace 不受影响）

**可接受的行为变化**：
- Crafter scenario：exploration drive 在低 imminent-threat 时刻能累积；urgency 大部分时间不再是 high
- 测试 data 调整（threat_signal_count 现在只算 imminent，老测试中包含 acquisition/capability 的需要改）

---

## 6. Architect gates

- G1：intake 写完，approved
- G2：1.B-4-a + 1.B-4-b 后，sensor 层失败测试 pass + Linux 等价性 verified
- G3：full slice 完成 + Crafter smoke 验证 exploration level 真起来 + 完整回归绿

---

## 7. 关键 follow-up（Round 1.D-5 还需做）

修完后，long-run 才有意义。1.D-5 仍然按计划——但这次跑出来的 exploration drive 数据会反映**真实 EVA 范式行为**，不是 framework bug 行为。
