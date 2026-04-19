# CodeRoblox Commands

## Core verification for the CodeRoblox runtime repo
```bash
source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"
make -C "$CODEROBLOX_ROOT" lint
make -C "$CODEROBLOX_ROOT" test
make -C "$CODEROBLOX_ROOT" build-plugin
make -C "$CODEROBLOX_ROOT" install-skill
make -C "$CODEROBLOX_ROOT" ci
```

## Start the local agent
```bash
source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"
python3 "$CODEROBLOX_ROOT/scripts/run_agent.py" --host 127.0.0.1 --port 8787
```

Do not switch the main workspace into `CODEROBLOX_ROOT` just to manage the runtime. Start the Roblox bridge runtime directly with Python and keep the user's real project directory as the active workspace.

## Install the Codex skill
```bash
source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"
make -C "$CODEROBLOX_ROOT" install-skill
```

## Build the Roblox Studio plugin
```bash
source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"
make -C "$CODEROBLOX_ROOT" build-plugin
```

Generated artifact:

```bash
echo "$CODEROBLOX_ROOT/build/CodeRobloxPlugin.rbxm"
```

PowerShell equivalents:

```powershell
. "$env:CODEROBLOX_ROOT\scripts\use-local-env.ps1"
make -C $env:CODEROBLOX_ROOT lint
make -C $env:CODEROBLOX_ROOT test
make -C $env:CODEROBLOX_ROOT build-plugin
make -C $env:CODEROBLOX_ROOT install-skill
make -C $env:CODEROBLOX_ROOT ci

python "$env:CODEROBLOX_ROOT\scripts\run_agent.py" --host 127.0.0.1 --port 8787

make -C $env:CODEROBLOX_ROOT install-skill

make -C $env:CODEROBLOX_ROOT build-plugin

$env:CODEROBLOX_ROOT\build\CodeRobloxPlugin.rbxm
```
