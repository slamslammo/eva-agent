# PR-O3 Canonical Run — 30-turn double-verification (COMPLETE)

Run: `validation-runs/ofc-canonical-run-20260530-125107/runtime` — ran to completion: exit_reason=max_steps, 30 turns / 31 deliberations, NOT recycled. Live deepseek-v4-pro dlPFC + OFC robust scoring + warmup fix + viz Phase A.

# PR-O3 canonical analysis — validation-runs/ofc-canonical-run-20260530-125107/runtime

- deliberations: **31**
- LLM-candidate coverage: 31/31 (100%) — dlPFC producer drove the run
- dlpfc_term active: 30/31 (97%) — PR-O2 rank wired into score
- release: 30 | withhold: 1 (3%) — vs T3 baseline ~62% withhold
- **dlPFC rank respected (rank0 released): 29/30 (97%)** — vs T3 62% flat-tie lost order
- release-action distribution: {'move_up': 8, 'move_right': 2, 'do': 8, 'move_left': 10, 'place_table': 1, 'make_wood_pickaxe': 1}

## per-deliberation trace

- delib0: acts=['move_right', 'move_up', 'move_down'] scores=[0.0, 0.0, 0.0] dlpfc_terms=[0.0, 0.0, 0.0] -> WITHHOLD
- delib1: acts=['move_up', 'move_down', 'move_right'] scores=[0.357, 0.237, 0.147] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib2: acts=['move_right', 'move_up'] scores=[0.373, 0.253] dlpfc_terms=[0.3, 0.18] -> move_right
- delib3: acts=['move_up', 'move_right'] scores=[0.385, 0.265] dlpfc_terms=[0.3, 0.18] -> move_up
- delib4: acts=['do', 'move_down'] scores=[0.588, 0.273] dlpfc_terms=[0.3, 0.18] -> do
- delib5: acts=['move_up', 'move_right'] scores=[0.398, 0.278] dlpfc_terms=[0.3, 0.18] -> move_up
- delib6: acts=['move_up', 'move_left', 'move_down'] scores=[0.402, 0.282, 0.192] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib7: acts=['move_right', 'move_left'] scores=[0.404, 0.284] dlpfc_terms=[0.3, 0.18] -> move_right
- delib8: acts=['do', 'move_down', 'move_left'] scores=[0.619, 0.286, 0.196] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib9: acts=['move_up', 'move_down', 'move_left'] scores=[0.408, 0.288, 0.198] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib10: acts=['move_left', 'move_up'] scores=[0.409, 0.289] dlpfc_terms=[0.3, 0.18] -> move_left
- delib11: acts=['do', 'move_right', 'move_down'] scores=[0.625, 0.289, 0.199] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib12: acts=['move_left', 'move_right', 'place_table'] scores=[0.41, 0.29, 0.284] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib13: acts=['do', 'place_table', 'move_right'] scores=[0.644, 0.374, 0.229] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib14: acts=['place_table', 'move_down'] scores=[0.494, 0.339] dlpfc_terms=[0.3, 0.18] -> place_table
- delib15: acts=['make_wood_pickaxe', 'move_right', 'move_up'] scores=[0.726, 0.353, 0.263] dlpfc_terms=[0.3, 0.18, 0.09] -> make_wood_pickaxe
- delib16: acts=['move_left', 'move_up', 'do'] scores=[0.482, 0.362, 0.458] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib17: acts=['move_left', 'move_up', 'move_right'] scores=[0.374, 0.254, 0.164] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib18: acts=['move_left', 'move_up'] scores=[0.379, 0.259] dlpfc_terms=[0.3, 0.18] -> move_left
- delib19: acts=['move_up', 'move_down', 'move_right'] scores=[0.382, 0.262, 0.172] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up
- delib20: acts=['move_left', 'move_up', 'move_down'] scores=[0.471, 0.351, 0.261] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib21: acts=['do', 'move_right'] scores=[0.554, 0.247] dlpfc_terms=[0.3, 0.18] -> do
- delib22: acts=['move_left', 'move_right'] scores=[0.374, 0.254] dlpfc_terms=[0.3, 0.18] -> move_left
- delib23: acts=['move_up', 'do', 'make_wood_sword'] scores=[0.466, 0.54, 0.498] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib24: acts=['move_left', 'move_up', 'move_down'] scores=[0.363, 0.243, 0.153] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib25: acts=['do', 'move_right'] scores=[0.556, 0.251] dlpfc_terms=[0.3, 0.18] -> do
- delib26: acts=['move_left', 'move_right', 'place_table'] scores=[0.376, 0.256, 0.172] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib27: acts=['do', 'move_up', 'move_down'] scores=[0.561, 0.26, 0.17] dlpfc_terms=[0.3, 0.18, 0.09] -> do
- delib28: acts=['move_up', 'move_down'] scores=[0.383, 0.263] dlpfc_terms=[0.3, 0.18] -> move_up
- delib29: acts=['move_left', 'move_down', 'make_wood_sword'] scores=[0.385, 0.265, 0.383] dlpfc_terms=[0.3, 0.18, 0.09] -> move_left
- delib30: acts=['move_up', 'move_left', 'place_table'] scores=[0.474, 0.354, 0.285] dlpfc_terms=[0.3, 0.18, 0.09] -> move_up

## viewer double-verification (ct_builder)
- ct_builder.build_turn_views: 31 TurnViews
- cognitive_trace rows: 607
- raw_observations files: 31
