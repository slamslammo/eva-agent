# Canonical 100-turn Run #2 — analysis (COMPLETE)

Run: `validation-runs/canonical-100turn-2-20260601-142750/runtime` — ran to natural
completion, NOT recycled / NOT prematurely killed (~1h53m, 14:27→16:20).
Live deepseek-v4-pro dlPFC on **main d2c578d** — the stack now carries the two
new observer-only instrumentation channels (world-map trace + anchor-domain-chain
trace), so this run validates both end-to-end on a real live run. EVA_TRACE=1.

## Exit summary (authoritative, from shutdown event)

- `exit_reason=max_steps`, `scenario_step=100` / `env_steps=100` / `turns=100`
- `final_life_state=STABLE`, `instance_valid=true`
- `step_attempts=104` = 100 env steps + 3 transport-infra + 1 first-frame withhold
- `infra_failures=3`, `withholds=1`, `deferred=0`

## Data completeness (all tracks self-consistent)

| track | count |
|---|---:|
| deliberation_audit.jsonl | 104 |
| cognitive_trace.jsonl | 2023 |
| raw_observations/ | 104 |
| **world_trace.jsonl** | **101** (1 base_map + 100 steps) |
| llm_transcripts/dlPFC/ | 104 |
| response_history / learning_outcomes | 100 / 100 |

## ★ New-channel validations (the point of run #2)

**① world_trace reconstructs the world** ✓
- base_map: 1 record, shape **[64, 64]**, seed 42.
- 100 step records, **all 100 carry player_pos**; 546 total tile_diffs.
- `reconstruct_from_trace(turn=100)` rebuilds the full 64×64 world — the
  observer channel works on a live run.

**② anchor chain reaches the trace** ✓
- 101/104 deliberations carry the anchor chain on their candidates'
  parameter_domain (the 3 gaps = the transport-infra turns with empty candidates).
- gate_branch distribution: **normal 88 / threat_response 13** (mostly calm;
  13 turns saw a visible threat and took the threat-response branch).
- Sample: feasible_actions=[do, move_down, move_left, move_right, move_up, noop],
  gate_branch={branch:normal, primary_pressure_reason:none, threat_visible:false,
  salience_critical:{}}. The full chain feasible → gate → A'(s) → candidates is
  now reconstructable from the audit.

**③ fairness invariant still holds with trace on** ✓
- 0/104 raw_observations carry forbidden keys (semantic / player_pos / position).
  The world-map channel writes the global map to world_trace.jsonl while the
  agent observation stays clean — fairness by construction, confirmed on a live run.

## OFC dlpfc-rank behavior (vs T3 baseline / run #1)

- LLM-candidate coverage: **101/104 (97%)** — dlPFC drove the run
- dlpfc_term active: **100/104 (96%)**
- release 100 | **withhold 4 (4%)** — vs T3 ~62%
- **dlPFC rank respected: 93/97 (96%)** — vs T3 62% flat-tie
- release-action distribution: move_up 29, move_left 24, move_right 17, do 16,
  move_down 8, place_table 2, make_wood_sword 2, make_wood_pickaxe 1,
  make_stone_pickaxe 1

Consistent with run #1 (rank ~96%, withhold 4%) — robust scoring holds at scale.

## Findings / differences vs run #1

- **water dipped to min 1.0** (run #1 min was 5.0) — this run came much closer to
  water-critical (food min 6.0, energy 6.0, health 9.0). The avatar still held
  STABLE for all 100 turns and never triggered the water-critical anchor branch
  (gate_branch never shows water_critical), but a min of 1.0 is a near-miss worth
  the viz/user analysis — same seed 42, so the difference traces to the live LLM's
  different action choices this run, not world layout. A behavior-level
  water-critical (anchor A'(s) contraction → walk into water) remains for a longer
  run; this run got closer than #1.
- **3 infra failures** all `llm_transport_unreachable` (turn 65/66/80) — transient
  DeepSeek drops, recovered next turn (same pattern as #1). max_tokens 4096 held;
  no empty-content / quota infra.
- capability progression: place_table → make_wood_pickaxe → make_wood_sword
  (similar to #1; furnace not reached this run).

## viewer double-verification (ct_builder)

- `ct_builder.build_turn_views`: **104 TurnViews** — every deliberation renders.
- world_trace.jsonl + anchor-chain fields are now available for B3's
  trace-viewer-v2 Band3 (world map V1 + anchor V3 chain view).

## Verdict

100-turn run #2 **complete and data-complete**, on the instrumented stack. Both
new observer channels validated end-to-end on a live run: world_trace
reconstructs the 64×64 world, the anchor chain reaches the audit, and the
fairness invariant holds (0 leaks). OFC rank/withhold consistent with #1. New
finding: water dipped to 1.0 (near-critical, vs 5.0 in #1). All tracks
self-consistent and viewer-renderable → ready for B3 viz + user data-quality
analysis. → G2_REQUESTED (run-report, not a code PR; no merge).
