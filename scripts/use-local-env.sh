#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODEROBLOX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PATH="$CODEX_HOME/bin:$PATH"

echo "CODEROBLOX_ROOT=$CODEROBLOX_ROOT"
echo "CODEX_HOME=$CODEX_HOME"
