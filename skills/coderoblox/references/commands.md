# CodeRoblox Commands

## Core verification
```bash
make lint
make test
make build-plugin
make ci
```

## Start the local agent
```bash
python3 scripts/run_agent.py --host 127.0.0.1 --port 8787
```

## Build the Roblox Studio plugin
```bash
make build-plugin
```

Generated artifact:

```text
build/CodeRobloxPlugin.rbxm
```
