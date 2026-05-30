# PR-O3 Canonical Run — 18-turn double-verification (partial, env-capped)

Run dir: `validation-runs/ofc-canonical-run-20260530-115146/runtime` (18/30 turns — environment recycled the 30-turn attempts; agent healthy, not early death).

# PR-O3 canonical analysis — validation-runs/ofc-canonical-run-20260530-115146/runtime

- deliberations: **18**
- LLM-candidate coverage: 18/18 (100%) — dlPFC producer drove the run
- dlpfc_term active: 17/18 (94%) — PR-O2 rank wired into score
- release: 17 | withhold: 1 (6%) — vs T3 baseline ~62% withhold
- **dlPFC rank respected (rank0 released): 17/17 (100%)** — vs T3 62% flat-tie lost order
- release-action distribution: {'move_up': 5, 'move_right': 4, 'move_left': 3, 'move_down': 2, 'do': 2, 'place_table': 1}

## per-deliberation trace

- delib0: acts=['move_right', 'move_down'] scores=[0.0, 0.0] dlpfc_terms=[0.0, 0.0] -> WITHHOLD
- delib1: acts=['move_up', 'move_right', 'move_down'] scores=[0.357, 0.237, 0.147] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib2: acts=['move_right', 'move_up'] scores=[0.373, 0.253] dlpfc_terms=[0.3, 0.18] -> move_right
- delib3: acts=['move_up', 'move_right'] scores=[0.385, 0.265] dlpfc_terms=[0.3, 0.18] -> move_up
- delib4: acts=['move_right', 'move_up', 'move_left'] scores=[0.393, 0.273, 0.183] dlpfc_terms=[0.3, 0.18, 0.09] -> move_right
- delib5: acts=['move_left', 'move_down'] scores=[0.398, 0.278] dlpfc_terms=[0.3, 0.18] -> move_left
- delib6: acts=['move_right', 'move_up'] scores=[0.402, 0.282] dlpfc_terms=[0.3, 0.18] -> move_right
- delib7: acts=['move_down', 'move_right', 'move_up'] scores=[0.404, 0.284, 0.194] dlpfc_terms=[0.3, 0.18, 0.09] -> move_down
- delib8: acts=['move_up', 'move_down', 'move_right'] scores=[0.406, 0.286, 0.196] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib9: acts=['do', 'move_down', 'move_left'] scores=[0.622, 0.288, 0.198] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib10: acts=['move_up', 'move_down'] scores=[0.409, 0.289] dlpfc_terms=[0.3, 0.18] -> move_up
- delib11: acts=['do', 'move_down', 'move_left'] scores=[0.625, 0.289, 0.199] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib12: acts=['place_table', 'move_up', 'move_left'] scores=[0.494, 0.29, 0.2] dlpfc_terms=[0.3, 0.18, 0.09] -> place_table
- delib13: acts=['move_up', 'move_left', 'move_down'] scores=[0.41, 0.29, 0.2] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib14: acts=['move_down', 'move_left'] scores=[0.41, 0.29] dlpfc_terms=[0.3, 0.18] -> move_down
- delib15: acts=['move_right', 'move_up', 'move_down'] scores=[0.41, 0.29, 0.2] dlpfc_terms=[0.3, 0.18, 0.09] -> move_right
- delib16: acts=['move_left', 'move_down', 'move_right'] scores=[0.41, 0.29, 0.2] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib17: acts=['move_left', 'move_up', 'move_right'] scores=[0.41, 0.29, 0.2] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left

## viewer double-verification (ct_builder)
- ct_builder.build_turn_views: 19 TurnViews
- cognitive_trace rows: 357
- raw_observations files: 18
