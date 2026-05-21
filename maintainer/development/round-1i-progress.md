# Round 1.I — Instrumented 短跑 → 分析 → 修可行性（计划②）— Progress（B）

**当前状态**：**I-1 DONE → G1_REQUESTED**（短跑 + 分析 + 报告完成，停等 A/用户敲定修法）。
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

## 后续 slice
- I-2（A/用户定后）：按选定修法改 producer（+ 可能 RPE）+ 补 bridge.resolve_action reason trace 缺口。
- I-3：同参再短跑确认 make_iron_* no-op 显著减少 + 仍 0 sleep + 无回归 → `G2_REQUESTED`。
