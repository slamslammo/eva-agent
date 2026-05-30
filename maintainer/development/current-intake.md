# Current Intake

## Active Item

`single-source-scenario-drive-metadata`（APPROVED → B-claude-2）

引入 `ScenarioDriveSpec` 作为 drive 元数据的**单一结构化权威源**，让 `DrivePreset`（的 drive
identity 部分）与 `DriveOntology` 都从它派生，消除两份并行权威源之间的**语义漂移**（代码里
metabolic 不再含 energy、ontology 仍写含 —— 结构性测试绿但 LLM 拿到错误本体）。

Coordination owner: `B-claude-2`
Branch: `single-source-scenario-drive-metadata`
（worktree `/Users/mojiawen/Documents/claude_projects/eva-agent-ssdm`，base `a48f59d`）

## Change Intake（6 点）

1. **层**：`l3_deliberation` ontology（framework 新建 `ScenarioDriveSpec`）+ `scenarios/crafter`
   （drive_preset / ontology 改为从 spec 派生）+ `l3_deliberation/llm_transcript`（填
   `drive_spec_version`）。
2. **canonical owner**：
   - `ScenarioDriveSpec` 类型 → 新建 `eva/scenario_drive_spec.py`（或 `eva/l3_deliberation/ontology/` 下）
   - Crafter drive 单一源 → `scenarios/crafter/`（新 `CRAFTER_DRIVE_SPEC`）
   - 派生的 `CRAFTER_DRIVE_ONTOLOGY` / `CRAFTER_DRIVE_PRESET` drive identity 部分 → 仍在 crafter，但 from spec
   - `drive_spec_version` 填值 → producer/transcript 接线
3. **stable / transitional / reserved**：framework ontology seam + Crafter scenario 均 stable。
   纯加法引入 spec + 改派生源，不扩 transitional 职责。
4. **slice or feature**：feature slice，拆 slice（见下）。
5. **需冻结的 tests**：
   - `tests/scenarios/crafter/test_ontology_consistency.py`（核心红线：
     `test_drive_ontology_covers_all_preset_drives` 断言 `ontology.names()==frozenset(preset.drive_types)`
     —— 单一源后应恒等；`test_effect_schema_drives_match_preset_drives` 同步）
   - `tests/scenarios/crafter/test_drive_preset.py` / `test_exploration_drive.py`（preset 行为不变）
   - `tests/l3_deliberation/test_ontology_modules.py`（`DriveOntology.names()` 单测）
   - `tests/l3_deliberation/test_llm_transcript_v11.py`（`drive_spec_version` 占位 → 填值后改断言）
   - Linux 回归（确认不被波及）
6. **需同步的 docs**：A review（framework 改动 + 范围收窄）；transcript schema 文档若提 v1.1
   drive_spec_version 现状需更新。

## ⚠️ 范围判断（偏离任务行预估 → 需 A 知情/确认）

任务行预估写「各 scenario 改造（**Crafter / Linux 都涉及**）」。但代码实证（a48f59d）显示：

- **Linux 没有 ontology**（无 `scenarios/linux_runtime/ontology/` 目录，只有 drive_preset 一份源）
  → Linux **不存在两源漂移**，本任务要解决的问题在 Linux 上不存在。
- **真正的漂移面只有 Crafter**（同时有 preset `drive_types` + ontology 文本，靠
  `test_ontology_consistency.py` 一条断言守 name 集合一致）。
- 强行让 Linux 也走 ScenarioDriveSpec 是**为对称而对称**，且任务行自己标了风险「Linux 也要动 →
  A 仔细 review 不破 Linux 回归」。

**决定（用户 2026-05-30 确认）**：本轮**只做 Crafter**。`ScenarioDriveSpec` 框架设计成**通用**
（Linux 未来若加 ontology 可接入），但本轮只 Crafter 接入，Linux drive_preset 不动 → 零 Linux 回归风险。
**这是对任务行 Crafter+Linux 预估的收窄，G2 时请 A 确认接受。**

**决定（用户 2026-05-30 确认）**：`DriveUpdatePolicy` 的 12 个行为调参（approach_rate/decay/
target_* 等）**留在 `drive_preset.py`**，不进 spec。spec 只管 drive identity / 语义
（name/meaning/low/high/typical_causes/relief_directions/dimensions/is_curiosity）。
职责清晰：spec = 「是什么 + 什么语义」，policy = 「怎么更新」。

## ScenarioDriveSpec 设计骨架

```python
# eva/scenario_drive_spec.py (framework, 新建)
@dataclass(frozen=True)
class DriveSpecEntry:
    name: str
    meaning: str
    low_means: str
    high_means: str
    typical_causes: tuple[str, ...] = ()
    relief_directions: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()   # 该 drive 绑定的 sensor 维度（派生 drive_type_by_dimension 反向）
    is_curiosity: bool = False         # 派生 curiosity_drive_type

@dataclass(frozen=True)
class ScenarioDriveSpec:
    version: str                       # 填 transcript drive_spec_version
    entries: tuple[DriveSpecEntry, ...]
    def drive_types(self) -> tuple[str, ...]
    def drive_type_by_dimension(self) -> dict[str, str]
    def curiosity_drive_type(self) -> str | None
    def build_drive_ontology(self) -> DriveOntology   # 派生 DriveOntologyEntry 元组
```

派生：`CRAFTER_DRIVE_SPEC`（唯一源）→ `CRAFTER_DRIVE_ONTOLOGY = spec.build_drive_ontology()`；
`CRAFTER_DRIVE_PRESET = DrivePreset(drive_types=spec.drive_types(),
drive_type_by_dimension=spec.drive_type_by_dimension(), default_policy=<行为参数保留>,
curiosity_drive_type=spec.curiosity_drive_type())`。一致性测试退化为同源恒等。

**不在范围**：SalienceSpec（free-text，无 per-drive 结构）；DriveUpdatePolicy（行为调参）；Linux。

## Slice 大纲（TDD）

- **slice 1**：framework 新建 `ScenarioDriveSpec` + `DriveSpecEntry` + 派生方法 + 单测
  （`drive_types` / `drive_type_by_dimension` / `curiosity_drive_type` / `build_drive_ontology`）。
- **slice 2**：Crafter 建 `CRAFTER_DRIVE_SPEC`（把现有 6 drive 的 preset+ontology 信息合并进单一源），
  `CRAFTER_DRIVE_ONTOLOGY` / `CRAFTER_DRIVE_PRESET` 改为从 spec 派生；保留 DriveUpdatePolicy 行为参数。
  字节级核对派生结果 == 原硬编码（行为/文本零变化）。
- **slice 3**：一致性测试退化为同源校验 + `drive_spec_version` 从 spec.version 填入 transcript。
- **slice 4**：全量回归（含 Linux 不受影响）+ 文档同步。

## 红线

- framework 改动 + 范围收窄，**A 必须 review**。
- 派生结果与原硬编码**字节/语义等价**（drive 行为、ontology 文本、prompt 输出零变化）。
- Linux drive_preset 不动。
- 每个 slice 一个 commit，先测试后实现（TDD）。
- DeepSeek key 只 inline 注入，绝不写 repo/git/board。

## Status：slice 1-4 全部完成 ✓（待 push + A G2 review）

| slice | 内容 | commit | 验证 |
|---|---|---|---|
| 1 | framework `ScenarioDriveSpec` + `DriveSpecEntry` + 4 派生方法 | `c3e5a18` | 13 测试 |
| 2 | Crafter `CRAFTER_DRIVE_SPEC` 单一源,preset+ontology 都从它派生 | `41cb912` | 等价性 8（vs oracle 快照）+ anti-drift 一致性 |
| 3 | `drive_spec_version` 填入 transcript + 结构性同源守卫 | `738b364` | slice3 4 测试 + placeholder 仍绿 |
| 4 | 全量回归 + Linux 不动核对 + docs review | 本次 | full **814 passed** |

intake doc commits：`e8b1c46`（设计+范围）+ 本次（收尾）。force-add（maintainer/ 本分支 gitignored）。

### 最终验证
- 全量 **814 passed**；`git diff --check` clean。
- **Linux 零改动**：`git diff a48f59d HEAD -- scenarios/linux_runtime/` 空；Linux 专项回归 22 passed。
- **等价性**：派生 ontology `format_text()` 与 refactor 前 oracle 快照字节一致；preset 三要素一致；
  DriveUpdatePolicy 行为参数零变化（approach/0.3/0.9/0.55/...）。
- **anti-drift 升级**：`test_drive_ontology_covers_all_preset_drives` 从"巧合相等"变为"构造保证"，
  新增 `test_both_derive_from_the_same_spec` 钉死同源。

### docs sync（已 review，无需改）
`docs/scenarios-SPEC.md` / `architecture-overview.md` / `blueprint-to-tracking-map.md` 只附带提到
`drive_preset`（仍是 bundle 组件、仍注册 exploration drive）—— 均无两源结构描述、不与 refactor 冲突。
`ScenarioDriveSpec` 是内部实现细节，公开文档非漂移权威源 → 不强改。

### 改动面（14 文件，scoped）
framework 3（spec 类型 + export + ScenarioOntology 加字段）、Crafter 4（spec + 派生 preset/ontology
+ registration + producer 接线）、tests 5、intake doc 1。无意外文件。

### A review 要点
1. **范围收窄**：任务行写 Crafter+Linux，实证 Linux 无 ontology/无漂移 → 本轮只 Crafter；
   spec 框架通用，Linux 未来可接。**请 A 确认接受收窄。**
2. DriveUpdatePolicy 留 preset（行为 vs identity 分离）。
3. drive_spec_version 接线：ScenarioOntology 新增可选字段 → producer 透传，None 时不影响 Linux/legacy。
4. 等价性以 oracle 快照钉死，非眼测。
