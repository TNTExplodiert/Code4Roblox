---
name: coderoblox
description: Use when working in the CodeRoblox repository or when connecting Codex to Roblox Studio through the local agent and plugin. Covers the repo-specific workflow for the Python agent, Roblox plugin, protocol changes, validation steps, and plugin installation expectations.
---

# CodeRoblox

Use this skill for work on the CodeRoblox repo, especially when the task involves the local agent, Roblox Studio plugin, shared protocol, tests, or the Studio connection flow.

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

## Runtime model
1. The local agent runs on `http://127.0.0.1:8787`.
2. The Roblox Studio plugin connects to that agent.
3. The plugin pushes snapshots from Studio.
4. The agent validates and queues operations.
5. The plugin polls for batches and reports results back.

## Important paths
- Agent entrypoint: `scripts/run_agent.py`
- Agent service: `src/coderoblox_agent/service.py`
- Agent server: `src/coderoblox_agent/server.py`
- Plugin entrypoint: `plugin/src/Main.server.luau`
- Shared protocol helpers: `plugin/src/Shared`
- CI: `.github/workflows/ci.yml`

## Commands
Read `references/commands.md` for the normal command set.

## Installation
Read `references/install.md` when the task is about installing or wiring together the plugin and the skill.
