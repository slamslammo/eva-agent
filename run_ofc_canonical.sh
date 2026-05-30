#!/bin/bash
# PR-O3 canonical run — OFC robust scoring + warmup fix + viz Phase A
# Usage: DEEPSEEK_API_KEY=<key> bash run_ofc_canonical.sh
#
# Verifies: PR-O3 G2 checklist §6 items 1-6, 9 (items 7-8 = viz Phase B, done after)
# Expected: ~30 turns, ~15-20 min with deepseek-v4-pro + thinking

set -e

RUNTIME_DIR="/tmp/ofc-canonical-run-$(date +%Y%m%d-%H%M%S)/runtime"
PYTHONPATH="/Users/mojiawen/Documents/claude_projects/eva-agent-ofc"
PYTHON="/opt/homebrew/opt/python@3.11/bin/python3.11"
MAX_TURNS=30
SEED=42

echo "[canonical] runtime dir: $RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"

PYTHONPATH="$PYTHONPATH" \
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:?Need DEEPSEEK_API_KEY}" \
  "$PYTHON" -m eva.kernel.main \
    --runtime-dir "$RUNTIME_DIR" \
    --max-turns "$MAX_TURNS" \
    --working-memory-model-client-mode live \
    --working-memory-model-client-provider deepseek \
    --working-memory-model-client-model deepseek-v4-pro \
    --seed "$SEED"

echo ""
echo "[canonical] run complete: $RUNTIME_DIR"
echo "[viz] start viewer: PYTHONPATH=$PYTHONPATH $PYTHON -m observation_tools --runtime-dir $RUNTIME_DIR --port 8283"
