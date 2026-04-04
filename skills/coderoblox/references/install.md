# Install and Connection Notes

## Codex skill
Install the repo skill by copying or symlinking `skills/coderoblox` into your Codex skills directory:

```text
$CODEX_HOME/skills/coderoblox
```

If `CODEX_HOME` is not set, the common default is:

```text
~/.codex/skills/coderoblox
```

## Claude
Claude does not use the Codex skill format directly. Use the repository `CLAUDE.md` as the project instruction file.

## Plugin and skill relationship
- The skill does not talk to Roblox Studio directly.
- The plugin talks to the local agent at runtime.
- The skill tells the AI which files, commands, and validation steps matter in this repository.
- In practice, the skill reduces prompt overhead and helps the AI use the plugin-agent architecture correctly.
