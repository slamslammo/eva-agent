# Canonical 100-turn Full-Flow Run — analysis (COMPLETE)

Run: `validation-runs/canonical-100turn-20260531-045908/runtime` — ran to natural
completion, **NOT recycled / NOT prematurely killed**. Live deepseek-v4-pro dlPFC
producer on the current integrated stack: main `2830fe4` (= OFC robust scoring +
single-source drive + single-source action + framework-timing advisor decoupling
+ warmup). User 2026-05-31 milestone.

## Exit summary (authoritative, from shutdown event)

- `exit_reason=max_steps` — reached the 100-turn cap cleanly
- `scenario_step=100` / `env_steps=100` / `turns=100` — full env coverage
- `step_attempts=104` = 100 env steps + 3 infra (transport) + 1 first-frame withhold
- `final_life_state=STABLE` / `instance_valid=true` — survived 100 turns
- `infra_failures=3` / `withholds=1` (shutdown counter) / `deferred=0`
- wall-clock ≈ 1h41m (04:59 → 06:40 CST); detached via nohup (survived session recycling)

## Data completeness (all tracks self-consistent)

| track | count | note |
|---|---:|---|
| deliberation_audit.jsonl | 104 | 100 released + 4 withheld |
| cognitive_trace.jsonl | 2039 | 12 transform nodes × deliberations + edges |
| raw_observations/ | 104 | one per deliberation attempt |
| llm_transcripts/dlPFC/ | 104 | live dlPFC call per attempt |
| response_history.jsonl | 100 | one per env step |
| learning_outcomes.jsonl | 100 | one per env step |
| llm_advisory_audit.jsonl | 104 | heuristic adapter (no redundant live advisory — framework-timing observation-2) |

104 attempts = 100 env_steps + 3 transport-infra + 1 first-frame withhold — exactly
reconciles with the shutdown counters.

## OFC dlpfc-rank behavior (vs T3 baseline / 30-turn)

- LLM-candidate coverage: **101/104 (97%)** — dlPFC producer drove the run (3 gaps = transport)
- dlpfc_term active: **100/104 (96%)** — PR-O2 rank wired into the score
- release: 100 | **withhold: 4 (4%)** — vs **T3 baseline ~62% withhold** (OFC robust scoring holds at scale)
- **dlPFC rank respected (rank0 released): 94/98 (96%)** — vs T3 62% flat-tie lost order
- dlpfc_terms stable at 0.3 / 0.18 / 0.09 (ranks 0/1/2) throughout — rank factor live every turn
- release-action distribution: move_left 31, do 19, move_down 16, move_right 14,
  move_up 13, place_table 2, make_wood_sword 2, make_wood_pickaxe 1,
  make_stone_pickaxe 1, place_furnace 1

## The 4 withholds — all explained (no anomaly)

- **delib0** — first-frame spawn: acts=['move_up','move_right','move_down'] all
  scores 0.0, dlpfc_terms 0.0 → WITHHOLD. Benign: the spawn frame has no drive /
  no dlpfc rank yet (identical to the 30-turn run's delib0). Not a defect.
- **delib85 / delib86 / delib91** — `acts=[]` (empty candidate set) → WITHHOLD.
  These are the **3 `llm_transport_unreachable` turns** (turn-0086/0087/0092): the
  live dlPFC producer returned empty when DeepSeek transport briefly dropped, the
  mediator withheld (default inhibition), and the next turn re-entered the same
  observation. **This is the framework's intended resilience** — LLM dropout
  degrades to substrate / withhold, the run does not crash or count a cognitive
  failure (shutdown classes them as infra_failures=3, distinct from the 1
  genuine cognitive first-frame withhold).

## Capability progression (a 100-turn finding)

The avatar advanced through the Crafter tool chain — visible in release actions:
place_table (delib10) → make_wood_pickaxe (15) → make_wood_sword (29, 31) →
place_furnace (67). The 30-turn run only reached make_wood_pickaxe; 100 turns let
the agent progress further (furnace = iron-crafting prerequisite). dlPFC drove
these via genuine score separation (e.g. delib15 make_wood_pickaxe 0.752 vs
move_right 0.29; delib29 make_wood_sword 0.587 vs move_right 0.411).

## water / food-critical: NOT triggered (consistent finding)

Across all 104 raw observations the vitals never reached critical:
- water min = **5.0**, food min = **6.0**, energy min = 6.0, health min = 9 (scale 0–9)

The avatar held STABLE for the full 100 turns — never entered metabolic crisis.
This matches the 30-turn observation (§6② "water-critical not reached, awaits a
longer run"). 100 turns still did not force water/food-critical — itself a
finding: under seed 42 the agent maintained vitals without ever being driven to
the water/food relief path. Behavior-level water-critical evidence (anchor A'(s)
contraction → walk into water tile → water rises) remains for a longer / different-
seed run (plan ③ 200+ turn).

## infra failures (3) — all transport, all recovered

All 3 `step_infra_failure` events are `reason=llm_transport_unreachable`
(turn-0086 @22:06, turn-0087 @22:09, turn-0092 @22:20) — transient DeepSeek
network drops, recovered by the next turn (run continued to 100). No max_tokens /
empty-content infra (the 4096 budget held), no API-quota failure. Not a blocker;
demonstrates the substrate-retry + withhold path under real upstream flakiness.

## viewer double-verification (ct_builder)

- `ct_builder.build_turn_views`: **104 TurnViews** — every deliberation renders
- cognitive_trace rows: 2039
- raw_observations files: 104

viz Phase A/B ingests the 100-turn run with no code change (per run-plan §3).
Ready for B3 viz-ingest + user data-quality / visualization analysis.

## Verdict

Full-flow 100-turn live canonical run **complete and data-complete**. OFC robust
scoring + dlpfc-rank hold at 100-turn scale (96% rank-respect, 4% withhold all
explained); framework resilience demonstrated under 3 real transport drops;
capability progressed to furnace; vitals held STABLE (water/food-critical still
awaits a longer run). All artifact tracks self-consistent and viewer-renderable.
→ G2_REQUESTED (run-report, not a code PR; no merge).
