#!/bin/bash
# canonical-100turn-full-flow-run — user 2026-05-31 milestone: full-flow 100-turn
# live canonical run on the current integrated stack (main 402d49d = OFC robust
# scoring + single-source drive + framework-timing advisor decoupling + warmup).
#
# Usage:  EVA_LLM_API_KEY=<key> bash run_canonical_100turn.sh
#   (base_url/model default to DeepSeek v4-pro; override via EVA_LLM_* env.)
#   The key is injected at call time only — NEVER written to this file / git / board.
#
# Same harness as the 30-turn OFC canonical run (run_ofc_canonical.sh), turns=100:
#   1. runner = runners.run_crafter (builds CrafterLLMActionProducer); plain
#      eva.kernel.main never constructs it.
#   2. needs BOTH --working-memory-backend llm_assisted AND
#      --working-memory-model-client-mode live.
#   3. live LLM resolved from EVA_LLM_* (NOT DEEPSEEK_API_KEY).
#   4. EVA_LLM_TRANSCRIPT=raw REQUIRED: producer stamps dlpfc_proposal_ref from
#      the transcript ref; without it OFC dlpfc-rank never applies.
#   5. dlPFC max_tokens=4096 (in run_crafter.py) — v4-pro reasoning eats 256.
#   6. runtime under validation-runs/ (persistent), NOT /tmp.
#   7. EVA_TRACE=1 emits cognitive_trace.jsonl + raw_observations/ for the viewer.
#   8. adapter_mode=heuristic (framework-timing observation-2 default) so NO
#      redundant per-turn advisory LLM call stacks on the dlPFC producer.
#
# Expected: 100 turns; v4-pro reasoning ≈ a few s–35s / dlPFC call. Detach via
# nohup; do NOT prematurely kill a slow-but-advancing run (30-turn lesson).
set -e

ROOT="/Users/mojiawen/Documents/claude_projects/eva-agent"
RUNTIME_DIR="$ROOT/validation-runs/canonical-100turn-$(date +%Y%m%d-%H%M%S)/runtime"
PYTHON="/opt/homebrew/opt/python@3.11/bin/python3.11"
MAX_TURNS="${MAX_TURNS:-100}"
SEED="${SEED:-42}"

mkdir -p "$RUNTIME_DIR"
echo "[canonical-100] runtime dir: $RUNTIME_DIR"
echo "[canonical-100] max_turns=$MAX_TURNS seed=$SEED model=${EVA_LLM_MODEL:-deepseek-v4-pro}"

EVA_TRACE=1 \
EVA_LLM_TRANSCRIPT=raw \
EVA_LLM_API_BASE_URL="${EVA_LLM_API_BASE_URL:-https://api.deepseek.com}" \
EVA_LLM_API_KEY="${EVA_LLM_API_KEY:?Need EVA_LLM_API_KEY (inject at call time; never commit it)}" \
EVA_LLM_MODEL="${EVA_LLM_MODEL:-deepseek-v4-pro}" \
PYTHONPATH="$ROOT" \
  "$PYTHON" -m runners.run_crafter \
    --runtime-dir "$RUNTIME_DIR" \
    --working-memory-backend llm_assisted \
    --working-memory-model-client-mode live \
    --working-memory-adapter-mode heuristic \
    --working-memory-model-client-timeout-sec 90 \
    --max-turns "$MAX_TURNS" \
    --seed "$SEED"

echo ""
echo "[canonical-100] run complete: $RUNTIME_DIR"
echo "[viz] start viewer: PYTHONPATH=$ROOT $PYTHON -m observation_tools --runtime-dir $RUNTIME_DIR --port 8283"
