#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${HOME}/apps/eva-agent"
RUNTIME_DIR="${HOME}/.local/state/eva-agent/runtime"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="eva-agent.service"

mkdir -p "$APP_DIR" "$RUNTIME_DIR" "$SYSTEMD_DIR"
cp deploy/systemd/user/${SERVICE_NAME} "$SYSTEMD_DIR/${SERVICE_NAME}"
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME"
systemctl --user status "$SERVICE_NAME" --no-pager || true
