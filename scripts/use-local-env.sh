#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODEROBLOX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PATH="$CODEX_HOME/bin:$PATH"
export CODEROBLOX_PLUGIN_FILE="${CODEROBLOX_ROOT}/build/CodeRobloxPlugin.rbxm"

if [[ -n "${ROBLOX_PLUGIN_DIR:-}" ]]; then
    export ROBLOX_PLUGIN_DIR
fi

echo "CODEROBLOX_ROOT=$CODEROBLOX_ROOT"
echo "CODEX_HOME=$CODEX_HOME"
echo "CODEROBLOX_PLUGIN_FILE=$CODEROBLOX_PLUGIN_FILE"
if [[ -n "${ROBLOX_PLUGIN_DIR:-}" ]]; then
    echo "ROBLOX_PLUGIN_DIR=$ROBLOX_PLUGIN_DIR"
else
    echo "ROBLOX_PLUGIN_DIR is not set"
fi
