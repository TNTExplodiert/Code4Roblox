# CodeRoblox Instructions for Codex

Use this repository for CodeRoblox work: a local Python agent, a Roblox Studio plugin, and the protocol between them.

## Project map
- `src/coderoblox_agent`: local HTTP agent
- `plugin/src`: Roblox Studio plugin
- `plugin/src/Shared`: protocol and shared helpers
- `plugin/tests`: Luau tests run with `lune`
- `tests`: Python tests
- `README.md`: setup, plugin installation, and workflow
- `implementation_plan.md`: product and architecture intent

## Working rules
- Keep the Python agent and Luau protocol in sync.
- After code changes, run `make ci`.
- If plugin code changes, also run `make build-plugin`.
- Do not introduce destructive Roblox operations without clear approval.
- Treat `rollback_checkpoint` and advanced playtest automation as partial or future work unless you implement them explicitly.

## Runtime workflow
1. Run `source scripts/use-local-env.sh`.
2. Work from `$CODEROBLOX_ROOT`.
3. Start the local agent with `python3 scripts/run_agent.py --host 127.0.0.1 --port 8787`.
4. Build the plugin with `make build-plugin`.
5. Install `$CODEROBLOX_ROOT/build/CodeRobloxPlugin.rbxm` as a local Roblox Studio plugin.
6. In Roblox Studio, set the plugin URL to `http://127.0.0.1:8787`, connect, then push a snapshot.

## Verification commands
```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make lint
make test
make build-plugin
make ci
```
