#!/bin/bash
cd /Users/mojiawen/Documents/claude_projects/eva-agent
exec python3 -m observation_tools \
  --runtime-dir /Users/mojiawen/Documents/claude_projects/eva-agent/validation-runs/scenario-time-model-run-final/runtime \
  --port 8282
