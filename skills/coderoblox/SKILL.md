---
name: coderoblox
description: Use when connecting Codex to Roblox Studio through the CodeRoblox agent runtime and plugin, or when maintaining the CodeRoblox repository itself. Covers the runtime workflow, plugin coordination, protocol changes, validation steps, and installation expectations.
---

# CodeRoblox

Use this skill when Codex should work with Roblox Studio through the CodeRoblox runtime and plugin, or when the task explicitly is to maintain the CodeRoblox repository itself.

The planning logic lives in the external AI that is using this skill. The local agent runtime is the state manager and local plugin endpoint, not the planner.

## Start here
- Read `README.md` for setup and installation steps.
- Read `implementation_plan.md` when a change affects product scope or protocol intent.
- Treat `src/coderoblox_agent` and `plugin/src/Shared` as coupled surfaces.

## Workspace rule
- Do not assume the user's active project workspace is the CodeRoblox repository.
- If the user is using this skill from another Roblox project, keep that project as the primary workspace and do not `cd` into `CODEROBLOX_ROOT` unless you are explicitly maintaining the CodeRoblox runtime/plugin itself.
- Use `CODEROBLOX_ROOT` only for runtime management tasks such as starting the local agent, building the plugin, or reinstalling the skill.
- Treat the current user project and the CodeRoblox runtime repo as separate locations when both are involved.
- Prefer absolute-path runtime commands like `source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"` or `python3 "$CODEROBLOX_ROOT/scripts/run_agent.py" ...` instead of changing the current working directory.
- Do not use `make` to start the Roblox bridge runtime. Start it directly with Python via `scripts/run_agent.py`.

## Working rules
- Keep the Python and Luau protocol shapes aligned.
- After code changes, run `make ci`.
- If plugin code changed, also run `make build-plugin`.
- Prefer additive, reviewable changes over hidden automation.
- Do not assume rollback, playtest automation, or diagnostics are fully implemented unless you verify and extend them.

## External KI workflow
1. Sync Studio context before planning.
2. Read the latest snapshot and relevant script documents from the local agent.
3. Prefer the local mirror under `studio_mirror/<project>/` for git-friendly file inspection when it is available.
4. Produce a plan in natural language first, then structured operations.
5. Include `preconditions.expected_source` and preferably `preconditions.expected_sha256` for script patches.
6. Assume the default execution mode is `auto_apply_safe`: normal non-destructive edits can flow through automatically, but destructive or high-risk work may still require plugin approval.
7. After apply, re-read the snapshot or script documents before making follow-up changes.
8. Never assume the latest Studio state unless the snapshot was synced recently.

## Runtime model
1. Run `source "$CODEROBLOX_ROOT/scripts/use-local-env.sh"` in Bash/WSL or `. "$env:CODEROBLOX_ROOT\scripts\use-local-env.ps1"` in PowerShell when you need the local runtime environment.
2. Only work from `$CODEROBLOX_ROOT` or `$env:CODEROBLOX_ROOT` when the task is to operate or modify the CodeRoblox runtime/plugin repo itself.
3. Start the local agent runtime directly with Python from `scripts/run_agent.py`, not through `make`.
4. The local agent runs on `http://127.0.0.1:8787`.
5. The Roblox Studio plugin connects to that local agent runtime and syncs Studio context.
6. The agent exposes snapshots, script documents, audit history, validation, and queued batches to the external AI.
7. The external AI plans changes and submits structured operations.
8. The plugin shows pending mutating batches for approval, then applies approved work and syncs the resulting Studio state back.

## Important paths
- Agent runtime entrypoint: `scripts/run_agent.py`
- Agent service: `src/coderoblox_agent/service.py`
- Agent HTTP endpoint: `src/coderoblox_agent/runtime_http.py`
- Plugin entrypoint: `plugin/src/Main.server.luau`
- Shared protocol helpers: `plugin/src/Shared`
- CI: `.github/workflows/ci.yml`

## Commands
Read `references/commands.md` for the normal command set.

## Agent endpoints to expect
- `GET /api/snapshots/latest?session_id=...`
- `GET /api/mirror?session_id=...`
- `GET /api/scripts?session_id=...`
- `GET /api/output?session_id=...`
- `GET /api/audit?session_id=...`
- `GET /api/operations/pending?session_id=...`
- `POST /api/operations/validate`
- `POST /api/operations/queue`
- `POST /api/operations/approve`
- `POST /api/operations/reject`

## Installation
Read `references/install.md` when the task is about installing or wiring together the plugin and the skill.
