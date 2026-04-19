# CodeRoblox Commands

## Core verification
```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make lint
make test
make build-plugin
make ci
```

## Start the local agent
```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
python3 scripts/run_agent.py --host 127.0.0.1 --port 8787
```

## Build the Roblox Studio plugin
```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make build-plugin
```

Generated artifact:

```bash
echo "$CODEROBLOX_ROOT/build/CodeRobloxPlugin.rbxm"
```

PowerShell equivalents:

```powershell
. .\scripts\use-local-env.ps1
Set-Location $env:CODEROBLOX_ROOT
make lint
make test
make build-plugin
make ci

python .\scripts\run_agent.py --host 127.0.0.1 --port 8787

make build-plugin

$env:CODEROBLOX_ROOT\build\CodeRobloxPlugin.rbxm
```
