#!/bin/bash
# PR-O3 canonical run — OFC robust scoring + dlpfc-rank, on the warmup-fixed +
# viz-integrated branch. Drives the LIVE dlPFC raw-action producer so the OFC
# dlpfc-rank scoring is actually exercised end-to-end.
#
# Usage:  EVA_LLM_API_KEY=<key> bash run_ofc_canonical.sh
#   (base_url/model default to DeepSeek v4-pro; override via EVA_LLM_* env.)
#
# Why this differs from the first draft (which silently produced a heuristic-only
# baseline — verified empty of LLM candidates):
#   1. runner = runners.run_crafter (builds CrafterLLMActionProducer); plain
#      eva.kernel.main never constructs it → heuristic fallback.
#   2. needs BOTH --working-memory-backend llm_assisted AND
#      --working-memory-model-client-mode live, or _build_candidate_producer
#      returns None.
#   3. live LLM is resolved from EVA_LLM_* (NOT DEEPSEEK_API_KEY).
#   4. EVA_LLM_TRANSCRIPT=raw is REQUIRED: the producer stamps dlpfc_proposal_ref
#      from the transcript ref; without it the OFC dlpfc-rank never applies.
#   5. max_tokens for the dlPFC call is raised in code (run_crafter.py) to 4096 —
#      deepseek-v4-pro reasoning otherwise eats the 256 budget → empty content →
#      needs_human_infra_failure.
#   6. runtime under validation-runs/ (persistent), NOT /tmp (which gets cleared
#      before archiving — prior data-loss lesson).
#
# Expected: 30 turns; deepseek-v4-pro reasoning ≈ 35s / dlPFC call → ~20–35 min.
set -e

ROOT="/Users/mojiawen/Documents/claude_projects/eva-agent-ofc"
RUNTIME_DIR="$ROOT/validation-runs/ofc-canonical-run-$(date +%Y%m%d-%H%M%S)/runtime"
PYTHON="/opt/homebrew/opt/python@3.11/bin/python3.11"
MAX_TURNS="${MAX_TURNS:-30}"
SEED="${SEED:-42}"

mkdir -p "$RUNTIME_DIR"
echo "[canonical] runtime dir: $RUNTIME_DIR"
echo "[canonical] max_turns=$MAX_TURNS seed=$SEED model=${EVA_LLM_MODEL:-deepseek-v4-pro}"

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
echo "[canonical] run complete: $RUNTIME_DIR"
echo "[viz] start viewer: PYTHONPATH=$ROOT $PYTHON -m observation_tools --runtime-dir $RUNTIME_DIR --port 8283"
