# Round 1.H — Viz P1 全链路埋点（P1a+P1b）— G1 Intake + Progress（B / 代码开发）

**当前状态**：**G1 APPROVED → 执行中**。**H-1 DONE**（TraceSink 基座 + run_meta + EVA_TRACE flag 接线、524 绿、flag-off 字节等价、端到端 run_meta 验证）。下一步 **H-2**（P1a 批1 emit）。
**分支**：`claude/recursing-hertz-7c4029`。
**依据**：`eva-coordination/telemetry-schema.md`（P0 冻结契约 v1，append-only）+ `viz-p1-instrumentation-startup-instruction.md`。
**Token**：**0**（纯发射、无 LLM）。

---

## 1. Feasibility = OK

- **0-token、opt-in**：`EVA_TRACE=1`（或等效 flag）开细粒度 + snapshot；普通跑不发、零额外开销。
- **架构**：flag-gated `TraceSink`（lifecycle 构造、threading 进 sensing/deliberation seam），按 `turn_index` 写 `cognitive_trace.jsonl` + 每 run 一条 `run_meta.json` + `raw_observations/`。
- **核心纪律（红线 #2）**：emit 调用**优先放 orchestration seam**（从各层**已返回的数据**组装信封+transform），**不往冻结 owner 函数体内插 emit**；仅当中间值确实只在 owner 函数体内可见时，才在该 owner 内加 **flag-gated 只读 hook**（flag-off no-op、字节等价）。
- round-1g 已把候选产出 / action_hint 因果点搬到 `run_deliberation` seam + bridge，故 batch-2 多数 `l3.*` 可在 seam 组装、无需碰冻结 owner 函数体。

## 2. 每 transform_id 发射位置归类（红线 #2 的逐条说明）

| transform_id | 发射位置 | 类别 | 备注 |
|---|---|---|---|
| `l1.raw_observation` | crafter wrapper / `CrafterRuntimeSession.step_action` | **seam** | `env.step` 已返回 obs；本轮新增 `raw_observations/` 持久化（9×7 grid + RGB）。flag-gated 写。 |
| `l1.threshold_classify` | `scenarios/crafter/sensors/avatar_state.py` | **seam 优先 / 待定 owner-hook** | 若分类输出（status/threat 分类）已下传到 signal 组装点 → seam 组装；若"哪个阈值触发"细节仅函数体内可见 → flag-gated 只读 hook。G1 标待定，H-2 落地时定。 |
| `l1.rate_sense` | `build_rate_context` 返回值的**调用者 seam** | **seam** | rate context 已是返回值。 |
| `l1.signal_publish` | `eva/l1_sensing/signal_bus.py` 发布点 seam | **seam** | 发布的 signals 是已组装结果。 |
| `l2.approach_delta`（每 drive） | `eva/l2_drive/drive_state.py::_approach_target_delta`（行 154） | **OWNER-HOOK** | 每-drive delta 仅在该函数体内可见 → flag-gated 只读 hook，**须证 flag-off 字节等价**。 |
| `l2.broadcast` | `build_drive_broadcast` 返回值的调用者 seam | **seam** | broadcast 已是返回值。 |
| `anchor.admit` | `run_deliberation` seam（`build_action_domain` / `admit_crafter_candidates` 返回的 domain+candidates） | **seam** | gate-state inputs（instance_valid/turn_allowed/critical_blocked/conservative_mode/life_state）取 `deliberation_input.runtime_gate_context`。 |
| snapshot `drive_state` | lifecycle / runtime seam（drive_broadcast 绝对值） | **seam** | 每 turn 各 drive 绝对值。 |
| `l3.candidate_produce` | `run_deliberation` 中 `active_producer.produce(...)` 之后 | **seam** | 发 base 候选集 + 每候选 `action_hint`（含 None）。round-1g 已建此 seam。 |
| `l3.assess_score` | `assess_candidates(...)` 返回值之后（runtime seam） | **seam** | OFC = 冻结 owner，**只读不改**。 |
| `l3.decide_release` | `decide_release(...)` 返回值之后（runtime seam） | **seam** | ⚠️ **anchor 更正**：实际在 `eva/l3_deliberation/peer_circuit/mediator.py::decide_release`，**非** instruction 写的 `selection.py`。冻结 owner、只读。 |
| `mediator.release` | `release_decision`（token/outcome）seam | **seam** | release_decision 已是返回值。 |
| `bridge.resolve_action` | lifecycle response_summary seam（`select_integrity_response`/`select_response_action` 返回的 `ResponseSelection`） | **seam** | **action_hint→执行因果点**：捕 `crafter_llm_action_hint_selection` 分支（reason + selected_action + release_context.action_hint）。这些都在 ResponseSelection / response record 里。 |
| snapshot `candidate_scoring` | `value_judgment.py::assess_candidates` 内打分分解 | **OWNER-HOOK** | `drive_weighted`(`drive_score`)/`projection`(`projection_score`)/`learning_bias`/`final`(`score`) 分解仅函数体内可见 → flag-gated 只读 hook。**advisory 已退役（round-1g）= 0/缺省**；habit 含于 learning_bias。**须证 flag-off 字节等价**。 |

**小结**：13 个 transform/ snapshot 中 **10 个纯 seam 组装**（不碰冻结 owner 函数体）；**2 个确定 owner-hook**（`l2.approach_delta`、`candidate_scoring`，flag-gated 只读、须证字节等价）；**1 个待定**（`l1.threshold_classify`，H-2 落地时按输出可见性定）。

## 3. 红线遵守（逐条）
1. **零决策语义改动**：emit 纯 additive；`EVA_TRACE` off → 全部 emit no-op、**字节等价**（同 round-1g model-off 标准）。
2. **冻结 owner 只读**：`value_judgment`(OFC)/`mediator`(decide_release/release)/`l1_sensing`/`l2_drive`/anchor policy/existence-semantics 决策逻辑**一行不改**；2 处 owner-hook 仅 flag-gated 只读 emit。
3. **append-only**：扩字段不改既有语义；transform_id 稳定（改名=新 id+alias）。
4. **opt-in**：`EVA_TRACE=1` 开；普通跑零开销。
5. **identity**：信封按 schema §2；`done=True`⇒`continuity_state="terminated"` 收尾、勿跨 individual 连轨。
6. **viewer 纯读**：本轮不碰 viewer。

## 4. 冻结 tests + 字节等价验证方案
- **全量回归 516 须仍全绿**（`EVA_TRACE` 未设 → emit no-op、无行为变更）。
- **新增 conformance test**（stub/local_rule_based、0 token）：`EVA_TRACE=1` 跑短 trace → 解析 `cognitive_trace.jsonl` 断言：(a) 按 `turn_index` 对齐可 replay；(b) 通用信封 + transform/snapshot 字段 schema 一致；(c) `run_meta.json` 填实非占位；(d) `done=True`→`terminated` identity 正确。
- **owner-hook 字节等价证明**：对 `drive_state` / `value_judgment` 加测试断言 flag-off 时输出（含 `to_dict`）与 baseline 逐字段一致；flag-on 仅多出 trace 文件、不改返回值。

## 5. slice 计划
- **H-1 ✅ DONE**：`TraceSink` 基座 + `run_meta` + 通用信封 + `EVA_TRACE` flag 接线。新 `eva/observability/{trace_sink.py,__init__.py}`（`TraceSink` 协议 / `NullTraceSink` no-op / `JsonlTraceSink` / `RunIdentity` / `build_trace_sink` / `trace_enabled` / `write_run_meta`）；main.py 构造 sink（flag-off→NullTraceSink）+ 写 `run_meta.json`（individual_id 解析后）+ 透传 LifecycleRuntime；lifecycle 存 `self.trace_sink`；`individual_terminated` 时置 `continuity_state=terminated`；runner 透传 `seed`。**8 单测**（flag 默认关 / Null 无文件 / Jsonl 信封 schema 一致 / snapshot / continuity 更新 / run_meta）。**全量回归 524 绿**（flag-off no-op 字节等价）。**端到端验**：`EVA_TRACE=1` local 短跑 → `run_meta.json` 填实（scenario/existence_semantics/seed/run_id 全有）、`cognitive_trace.jsonl` 正确缺省（H-1 无 per-layer emit）。`validation-runs/round-1h-h1/`（gitignored）。
- **H-2 TODO**：P1a 批1（`l1.*` + `l2.*` + `anchor.admit` + `drive_state` snapshot + `raw_observations/`）→ 自证 schema 一致 + flag-off 字节等价 + 回归绿。emit 调用从 sensing/runtime seam 组装；`l2.approach_delta` flag-gated 只读 hook。
- **H-3 TODO**：P1b 批2（`l3.*` + `mediator.release` + `bridge.resolve_action` 因果点 + `candidate_scoring` snapshot）→ 同样自证。多数 `run_deliberation` seam 组装；`candidate_scoring` flag-gated 只读 hook。
- **H-4 TODO**：conformance 短 trace（stub、0 token）+ 字节等价自证 → 置 `G2_REQUESTED`。

## 6. 请 A 裁（G1）
1. **2 处 owner-hook 判断**（`l2.approach_delta`、`candidate_scoring`）：同意"flag-gated 只读 hook + 字节等价证明"作为唯一进 owner 函数体的例外？
2. **anchor 更正**：`l3.decide_release` 实际锚 = `mediator.py::decide_release`（非 `selection.py`），registry 是否 append alias 备注？
3. `l1.threshold_classify` 留待 H-2 按输出可见性定（seam 优先），可否？
