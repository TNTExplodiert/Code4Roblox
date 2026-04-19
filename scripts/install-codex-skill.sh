#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CODEROBLOX_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

mkdir -p "$CODEX_HOME/skills"
rm -rf "$CODEX_HOME/skills/coderoblox"
mkdir -p "$CODEX_HOME/skills/coderoblox"
cp -R "$CODEROBLOX_ROOT/skills/coderoblox/." "$CODEX_HOME/skills/coderoblox"

echo "Installed Codex skill at $CODEX_HOME/skills/coderoblox"
