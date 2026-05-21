# Round 1.I — Instrumented 短跑 → 分析 → 修可行性（计划②）— Progress（B）

**当前状态**：**I-3 DONE → G2_REQUESTED**（全 slice 完成）。I-1（分析）+ G1（A 定 a2）+ I-2（动态可行 vocab，535 绿）+ I-3（live 确认：make_iron_* no-op 8/9→0/9、得 1 achievement、0 塌缩）完成。待 A 终审。
**分支**：`claude/recursing-hertz-7c4029`。指令 `eva-coordination/round-1i-instrumented-shortrun-craftability-fix-startup-instruction.md`。

---

## I-1：instrumented live 短跑 + 原始 trace 分析（2026-05-22）

**跑**：`EVA_TRACE=1` + `llm_assisted` live（DeepSeek）+ seed=1 + 12 turns。产物 `validation-runs/round-1i/i1-live/`（gitignored）：`cognitive_trace.jsonl` + `run_meta.json` + `raw_observations/`。**花费 ~¥0.03**（advisory 15.8K tokens/10 calls + producer ~同量 ≈ ~32K，≪¥0.18 预批；0 fallback）。

### 发现（直接读原始 cognitive_trace.jsonl + response_history）

1. **✅ action_hint 因果路径完好**：9/9 response `selected_action == LLM action_hint`、`selected_action_reason=crafter_llm_action_hint_selection`；trace 内 `l3.candidate_produce`(hint) → `bridge.resolve_action`(exec) 每 turn 对齐。round-1g 的 lever 在 live 下稳定工作。
2. **🔴 行为问题确认 + 量化**：escalate posture 的 8/9 turn，LLM 选 `make_iron_sword`/`make_iron_pickaxe`，**全部 `outcome=unchanged`（no-op）**——inventory 无变化、`achievement_delta=0`。**不是随机乱选，是系统性"够顶级工具"偏置**：每个 escalate turn 都挑最高级 iron 工具，但 agent 无 iron/furnace/table → Crafter no-op。
3. **✅ 0 passivity 回潮**：sleep 0/9。drive 锁 escalate、LLM 保持主动（虽不可行）——round-1f 的 90% sleep 不复现，结构防 passivity 成立。
4. **根因（读 producer 代码 `llm_candidate_producer._build_messages`，round-1g G-6 写的）**：prompt 给 LLM 的是 `top_drive` + `drive_levels` + `options_per_posture`（profile 的 eligible 动作**全集**）+ `situation_key`——**没给 inventory，也没给 craftability（当前实际能造什么）**。LLM 从"语法可选"里挑最高级的，不知道造不出来。
5. **🟡 次要 trace 缺口（非行为问题）**：`bridge.resolve_action` 的 `selected_action_reason` 在 `cognitive_trace.jsonl` 里显示 None（我从 in-memory `response_summary` emit、该 dict 缺此键），但持久化的 `response_history` 该字段正确=`crafter_llm_action_hint_selection`。→ I-2 顺手补 trace payload（同 A 提的 l1.rate_sense 测试缺口级别）。

### 修法设计（答指令 §2 设计点 + 候选方案，请 A/用户裁）

**设计点**：可行性数据 = **scenario-owned（Crafter 知 inventory/craftability）**，须经注入流入 producer，**不破 producer framework-generic 边界**（producer 不得 import Crafter）。

**候选修法**：
- **(a1)** producer prompt 注入"inventory + 简要 craftability 文本"：runner 已注入 `profile_action_vocab`（scenario-owned），同理注入一个**每-turn 可行性 context**（scenario 提供的 callable 或经 `deliberation_input.working_memory_context` 携带 inventory + 可造列表），producer 当不透明 context 折进 prompt。
- **(a2)（B 推荐）** **动态可行 vocab**：把 `profile_action_vocab` 从静态 map 改为 scenario 提供的**每-turn callable**，按当前 inventory 过滤掉造不出的动作（make_iron_* 在没 iron 时根本不进 options）→ LLM **选不到**不可行动作。比 (a1) 更干净（不靠 LLM "读懂"可行性，直接不 offer）。代价：vocab 注入接口从 map 改 callable（producer 仍 generic、scenario 提供逻辑）。
- **(b) 辅助** RPE 罚 `outcome=unchanged`：给 no-op 负 bias 让其学着避开（慢、学习式、补充）。动 `peer_circuit/rpe.py` 须小心、只加 unchanged 罚不改既有语义。

**B 倾向**：(a2) 为主（结构性杜绝、最干净）；(b) 辅（长期学习）。**红线**：producer(`llm_candidate_producer.py`) 非冻结可改；OFC/mediator/peer_circuit/anchor/L1/L2/existence-semantics 冻结；model-off 字节等价。

**→ 置 `G1_REQUESTED`，停等 A/用户定 (a1) vs (a2) + 是否带 (b)。**

## I-2 — 修可行性（a2 动态可行 vocab）（2026-05-22）

A/用户裁定 = **(a2) 动态可行 vocab 为主、不带 (b)**。实现：
- **新 `scenarios/crafter/actions/feasibility.py`**（Crafter-owned，可知 recipe）：按 `crafter/data.yaml` 的 `make_*`/`place_*` 的 `uses`(inventory) + `nearby`(table/furnace) 要求，`feasible_profile_action_vocab(observation)` 把 `PROFILE_ELIGIBLE_ACTIONS` 过滤成**本 turn 物理可行**子集。**红线 ④**：只剔物理不可行（缺料/缺 nearby），**绝不按 usefulness 剔**；noop/sleep/move_*/do 无 requirement 永远可行 → **每 posture ≥ 默认动作、永不空集**（A 条件 ②，结构性满足 + 显式兜底）。nearby 用 local_view cells 出现判定（保守过近似、只在材料完全不在视野时剔，绝不过滤可行动作）。
- **producer 改 callable vocab**：`LLMCandidateProducer.profile_action_vocab` 接受 `Mapping | Callable[[], Mapping]`，每 `produce()` 解析（`_resolve_vocab`）。静态 dict 仍兼容（测试）。**producer 仍 framework-generic、不 import Crafter**。
- **runner 闭包注入**：`_build_candidate_producer(config, session)` 注入 `lambda: feasible_profile_action_vocab(session.latest_agent_observation)`——scenario-owned 可行性经闭包流入、不扩冻结契约（A 条件 ①）。
- **trace 缺口补**（A 条件 ③）：`build_response_summary` 加 `selected_action_reason`（持久 response_history 本就有；events 只读 named keys → **persisted 字节等价**）→ `bridge.resolve_action` trace 不再 None。
- **测试**：feasibility 7（make_iron 缺料剔 / make_wood 需 table / place 按 inventory / 永远可行不剔 / 只剔不增+默认在 / 纯 helper）+ producer callable vocab 1（infeasible hint 丢弃）+ conformance 加断言 reason 非 None。**全量回归 535 绿**、flag-off/model-off 字节等价、未触 OFC/mediator/peer_circuit/anchor/L1/L2/existence-semantics 决策逻辑。
- **范围注**：(a2) 只消 no-op（不 offer 造不出的动作），**不保证选"最推进科技树"**——那属蓝图 §7.4 多步规划、后轮（A 已注明）。

**→ I-2 DONE。暂停交用户跑 I-3 live 确认**（同参再短跑 ~¥0.03，用户在场）。

## I-3 — 再短跑确认 ✅（2026-05-22，用户唤醒跑）

同 I-1 参数（`EVA_TRACE=1`+live+seed=1+12turn，`validation-runs/round-1i/i3-live`，~¥0.03）。读原始 trace，**I-1 vs I-3 对比**：

| 指标 | I-1（修前） | I-3（修后 a2） |
|---|---|---|
| `make_iron_*` no-op | **8/9** | **0/9** ✅ |
| LLM 选动作 | 全 iron 工具（造不出） | `do`×6（真交互）/ sleep×2 / noop×1 |
| achievements | 0 | **1**（t6 `do`→collect_sapling，inv+sapling） |
| action_hint 因果 | exec==hint | exec==hint（仍完好） |
| sleep | 0/9 | 2/9（stabilize posture 内合理、非 round-1f 塌缩） |

**结论**：(a2) 动态可行 vocab **彻底消除造不出的 no-op**（make_iron_* 0/9），LLM 改选可行 `do` 并拿到 1 个 achievement（真进展）；action_hint 因果完好；无 passivity 塌缩（escalate `do` 主导）。残留 `unchanged` = pressure-relief 指标 + 未链式推进科技树（§7.4 多步规划、后轮范围、A 已注非本轮）。**本轮目标（消 no-op）达成 → 置 `G2_REQUESTED`**（A 终审，专核红线 ④ feasibility-only：vocab 只剔物理不可行）。
