# CodeRoblox Instructions for Codex

Use this repository for CodeRoblox work: a local Python agent, a Roblox Studio plugin, and the protocol between them.

## Project map
- `src/coderoblox_agent`: local agent runtime and plugin endpoint
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
- The external AI does the planning. The local agent should expose state, context, validation, and approvals rather than silently inventing plans on its own.

## Runtime workflow
1. Run `source scripts/use-local-env.sh` in Bash/WSL or `. .\scripts\use-local-env.ps1` in PowerShell.
2. Work from `$CODEROBLOX_ROOT` or `$env:CODEROBLOX_ROOT`.
3. Start the local agent with `python3 scripts/run_agent.py --host 127.0.0.1 --port 8787`.
4. Set local machine paths like `ROBLOX_PLUGIN_DIR` via environment variables, not in repo files.
5. Build the plugin with `make build-plugin`.
6. Install `$CODEROBLOX_PLUGIN_FILE` as a local Roblox Studio plugin, or let `make build-plugin` copy it automatically when `ROBLOX_PLUGIN_DIR` is set.
7. In Roblox Studio, set the plugin URL to `http://127.0.0.1:8787`, connect, and sync Studio context.
8. Treat mutating batches as reviewable work only when the batch is high-risk or the session explicitly uses manual review mode.

## Verification commands
```bash
source scripts/use-local-env.sh
cd "$CODEROBLOX_ROOT"
make lint
make test
make build-plugin
make install-skill
make ci
```
