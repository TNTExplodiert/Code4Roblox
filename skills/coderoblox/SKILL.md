---
name: coderoblox
description: Use when working in the CodeRoblox repository or when connecting Codex to Roblox Studio through the local agent and plugin. Covers the repo-specific workflow for the Python agent, Roblox plugin, protocol changes, validation steps, and plugin installation expectations.
---

# CodeRoblox

Use this skill for work on the CodeRoblox repo, especially when the task involves the local agent, Roblox Studio plugin, shared protocol, tests, or the Studio connection flow.

The planning logic lives in the external AI that is using this skill. The local agent is a tool server and state manager, not the planner.

## Start here
- Read `README.md` for setup and installation steps.
- Read `implementation_plan.md` when a change affects product scope or protocol intent.
- Treat `src/coderoblox_agent` and `plugin/src/Shared` as coupled surfaces.

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
6. Treat all mutating operations as reviewable work that must pass through the plugin approval gate.
7. After apply, re-read the snapshot or script documents before making follow-up changes.
8. Never assume the latest Studio state unless the snapshot was synced recently.

## Runtime model
1. Run `source scripts/use-local-env.sh` in Bash/WSL or `. .\scripts\use-local-env.ps1` in PowerShell.
2. Work from `$CODEROBLOX_ROOT` or `$env:CODEROBLOX_ROOT`.
3. The local agent runs on `http://127.0.0.1:8787`.
4. The Roblox Studio plugin connects to that agent and syncs Studio context.
5. The agent exposes snapshots, script documents, audit history, validation, and queued batches to the external AI.
6. The external AI plans changes and submits structured operations.
7. The plugin shows pending mutating batches for approval, then applies approved work and syncs the resulting Studio state back.

## Important paths
- Agent entrypoint: `scripts/run_agent.py`
- Agent service: `src/coderoblox_agent/service.py`
- Agent server: `src/coderoblox_agent/server.py`
- Plugin entrypoint: `plugin/src/Main.server.luau`
- Shared protocol helpers: `plugin/src/Shared`
- CI: `.github/workflows/ci.yml`

## Commands
Read `references/commands.md` for the normal command set.

## Agent endpoints to expect
- `GET /api/snapshots/latest?session_id=...`
- `GET /api/mirror?session_id=...`
- `GET /api/scripts?session_id=...`
- `GET /api/audit?session_id=...`
- `GET /api/operations/pending?session_id=...`
- `POST /api/operations/validate`
- `POST /api/operations/queue`
- `POST /api/operations/approve`
- `POST /api/operations/reject`

## Installation
Read `references/install.md` when the task is about installing or wiring together the plugin and the skill.
