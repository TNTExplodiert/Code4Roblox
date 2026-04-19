# Install and Connection Notes

## Codex skill
Install the repo skill by linking `skills/coderoblox` into your Codex skills directory.

```bash
source scripts/use-local-env.sh
./scripts/install-codex-skill.sh
```

Installed location:

```bash
echo "$CODEX_HOME/skills/coderoblox"
```

PowerShell:

```powershell
. .\scripts\use-local-env.ps1
. .\scripts\install-codex-skill.ps1
$env:CODEX_HOME\skills\coderoblox
```

## Claude
Claude does not use the Codex skill format directly. Use the repository `CLAUDE.md` as the project instruction file.

## Plugin and skill relationship
- The skill does not talk to Roblox Studio directly.
- The plugin talks to the local agent at runtime.
- The skill tells the AI which files, commands, and validation steps matter in this repository.
- In practice, the skill reduces prompt overhead and helps the AI use the plugin-agent architecture correctly.

## Working from another project
- Installing this skill does not mean the active project workspace should move into the CodeRoblox repository.
- Keep your actual Roblox project in its own folder.
- Use the CodeRoblox repository only as the location of the runtime, plugin source, and installation scripts.
- When the AI is editing your game or local project files, it should stay in that project workspace unless you explicitly ask it to modify the CodeRoblox runtime repo.
- Runtime commands should be executed via absolute paths or `make -C "$CODEROBLOX_ROOT" ...`, not by relocating the main working directory into the runtime repo.
- The Roblox bridge runtime itself should be started directly with Python from `scripts/run_agent.py`, not via `make`.
