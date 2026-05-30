# Current Intake

## Active Item

`single-source-crafter-action-metadata`（APPROVED → B-claude-2）

drive 同源的对称 follow-up：把 Crafter raw-action 元数据从两份并行硬编码源
（`actions/compatibility.ALL_ACTIONS` 17 + `crafter_action_ontology` 17）收敛成单一
`ScenarioActionSpec` 派生。复用刚做完的 `ScenarioDriveSpec` 套路。

Coordination owner: `B-claude-2`
Branch: `single-source-crafter-action-metadata`
（worktree `/Users/mojiawen/Documents/claude_projects/eva-agent-action`，base `402d49d`）

准则来源：`eva-coordination/plans/single-source-remediation-plan.md` §8。

## 排序说明

A 排序：本任务排在 `canonical-100turn-full-flow-run` 之后（run 是用户 milestone critical
path）。但 run 当前卡 NEEDS_HUMAN（EVA_LLM key 缺失，等用户注入）；**用户 05-31 拍板：
等 key 窗口先做 action 任务**（不依赖 run、零 token、纯重构）。run 一注入 key 即插入。

## Change Intake（6 点）

1. **层**：`l3_deliberation` ontology（framework 新建 `ScenarioActionSpec`）+ `scenarios/crafter`
   （`ALL_ACTIONS` + action ontology 改为从 spec 派生）。
2. **canonical owner**：`ScenarioActionSpec` → `eva/l3_deliberation/ontology/scenario_action_spec.py`；
   Crafter action 单一源 → `scenarios/crafter/action_spec.py`（新）；派生 `ALL_ACTIONS`（compatibility.py）
   + `CRAFTER_ACTION_ONTOLOGY`（ontology）。
3. **stable owner**，纯加法引入 spec + 改派生源，不扩 transitional 职责。
4. **feature slice**，拆 4 slice。
5. **冻结 tests**：`tests/scenarios/crafter/test_ontology_consistency.py`（action 名集守 +
   effect-schema 17×6 基数 + action 轴对齐）；framework `test_ontology_modules.py`（ActionOntology）。
6. **docs**：A review（framework 改动）；按 §8 准则。

## 设计（镜像 ScenarioDriveSpec）

```python
# eva/l3_deliberation/ontology/scenario_action_spec.py
@dataclass(frozen=True)
class ActionSpecEntry:
    action: str
    effect: str
    details: tuple[str, ...] = ()
    typical_use: str | None = None   # 与 ActionOntologyEntry 1:1
@dataclass(frozen=True)
class ScenarioActionSpec:
    version: str
    entries: tuple[ActionSpecEntry, ...]
    def action_names(self) -> tuple[str,...]   # 重复名即 raise
    def build_action_ontology(self) -> ActionOntology
```

派生：`CRAFTER_ACTION_SPEC`（唯一源）→ `ALL_ACTIONS = CRAFTER_ACTION_SPEC.action_names()`；
`CRAFTER_ACTION_ONTOLOGY = CRAFTER_ACTION_SPEC.build_action_ontology()`。

**确认无设计岔路**（§8 G1 escalate 触发条件）：action↔ontology 严格 1:1（17=17），
effect-schema 用 action-family row 模板按 action 名展开 → action 轴天然随 ALL_ACTIONS 钉死，
**不需要拆独立 spec**。无歧义 → 走 G2，不 escalate G1。

**注意边界**：`compatibility.py` 同时是 bridge executor（NOOP_ACTION 等常量 + select_response_action
逻辑），只让 `ALL_ACTIONS` 元组从 spec 派生，**常量定义 + bridge 逻辑保留不动**。

## Slice 大纲（TDD）

- **slice 1**：framework `ScenarioActionSpec` + `ActionSpecEntry` + 派生 + 单测。✅
- **slice 2**：Crafter `CRAFTER_ACTION_SPEC` 单一源，`ALL_ACTIONS` + `CRAFTER_ACTION_ONTOLOGY`
  从它派生；vs PRE-refactor oracle 字节等价。
- **slice 3**：effect-schema action 轴对齐测试（轴 == spec.action_names()）+ 一致性测试同源化。
- **slice 4**：全量回归（Linux 零 diff）+ docs + G2。

## 红线（§8）

- **迁移保真 oracle 来自 PRE-refactor `402d49d` 旧代码**，不得从新 spec 自产（防循环，A 独立重算复核）。
- effect-schema action 轴随单一 spec 钉死（axis-alignment 测试）。
- drift-by-construction（ontology 名集 == ALL_ACTIONS）。
- Crafter-only，`scenarios/linux_runtime` 零 diff。
- full 套件绿。每 slice 一 commit，先测试后实现。
- 遇 action 专属设计岔路 → escalate G1（本任务已确认无岔路）。

## Status

- slice 1（ScenarioActionSpec framework 类型 + 派生）：完成 ✓（oracle 已抓，PRE-refactor）。
