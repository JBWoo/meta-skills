# Jangpm Meta Skills for Claude Code and Codex

A collection of meta skills for designing agent systems, clarifying requirements, wrapping up sessions, and automatically optimizing skills.

- Claude Code distribution: `.claude/`
- Codex distribution: `.codex/skills/`

## Skills

| Skill | Role | Claude Code | Codex |
|---|---|---|---|
| `blueprint` | Design document for automation/agent systems | `/blueprint` command + skill | `blueprint` 또는 `$blueprint` |
| `deep-dive` | Multi-round interview to produce a detailed spec document | `/deep-dive` command + skill | `deep-dive` 또는 `$deep-dive` |
| `reflect` | Summarize a work session, identify doc update points, surface next actions | `/reflect` command + skill | `reflect` 또는 `$reflect` |
| `autoresearch` | Automated skill optimization (iterative runs + evaluation + prompt mutation) | `/autoresearch` skill | `autoresearch` 또는 `$autoresearch` |

## Skill Workflow

These four skills work best in sequence:

```
blueprint → deep-dive → [implement] → autoresearch → reflect
```

| Step | Skill | When to use |
|------|-------|-------------|
| 1. Design | `blueprint` | Start here for any new agent/automation — produces a complete design document before writing code |
| 2. Spec | `deep-dive` | When requirements need more clarity — structured interview produces a spec document |
| 3. Implement | *(your code)* | Build the system following the blueprint and spec |
| 4. Optimize | `autoresearch` | After the skill works — iteratively improve it using automated eval loops |
| 5. Wrap up | `reflect` | At the end of any work session — summarize, log learnings, surface follow-up actions |

**Shorter patterns:**
- New project: `blueprint` → `deep-dive` → implement → `autoresearch` → `reflect`
- Mid-project feature: `deep-dive` → implement → `reflect`
- Skill optimization: `autoresearch` standalone
- Session end: `reflect` standalone

## Repository Structure

```text
.claude/
  commands/
  skills/

.codex/
  skills/
    autoresearch/
    blueprint/
    deep-dive/
    reflect/
```

## Installing (Codex)

Codex users can copy the four skill folders to `~/.codex/skills/`.

### Windows PowerShell

```powershell
Copy-Item -Recurse .\.codex\skills\autoresearch "$env:USERPROFILE\.codex\skills\"
Copy-Item -Recurse .\.codex\skills\blueprint   "$env:USERPROFILE\.codex\skills\"
Copy-Item -Recurse .\.codex\skills\deep-dive   "$env:USERPROFILE\.codex\skills\"
Copy-Item -Recurse .\.codex\skills\reflect     "$env:USERPROFILE\.codex\skills\"
```

### macOS / Linux

```bash
cp -r ./.codex/skills/autoresearch ~/.codex/skills/
cp -r ./.codex/skills/blueprint    ~/.codex/skills/
cp -r ./.codex/skills/deep-dive    ~/.codex/skills/
cp -r ./.codex/skills/reflect      ~/.codex/skills/
```

## Installing (Claude Code)

The existing Claude Code distribution method is also preserved.

### Windows PowerShell

```powershell
Copy-Item -Recurse .\.claude\skills\autoresearch "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse .\.claude\skills\blueprint   "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse .\.claude\skills\deep-dive   "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse .\.claude\skills\reflect     "$env:USERPROFILE\.claude\skills\"

Copy-Item .\.claude\commands\blueprint.md  "$env:USERPROFILE\.claude\commands\"
Copy-Item .\.claude\commands\deep-dive.md  "$env:USERPROFILE\.claude\commands\"
Copy-Item .\.claude\commands\reflect.md    "$env:USERPROFILE\.claude\commands\"
```

### macOS / Linux

```bash
cp -r ./.claude/skills/autoresearch ~/.claude/skills/
cp -r ./.claude/skills/blueprint    ~/.claude/skills/
cp -r ./.claude/skills/deep-dive    ~/.claude/skills/
cp -r ./.claude/skills/reflect      ~/.claude/skills/

cp ./.claude/commands/blueprint.md ~/.claude/commands/
cp ./.claude/commands/deep-dive.md ~/.claude/commands/
cp ./.claude/commands/reflect.md   ~/.claude/commands/
```

## Codex vs Claude Code differences

- Removed the Claude-specific `/commands` wrappers and restructured around `SKILL.md` as the central entry point.
- Updated `.claude/...` paths, `Task`-based subagents, and `AskUserQuestion` assumptions to fit the Codex flow.
- `blueprint` includes a Codex-compatible document template, design principles, and a structure validation script.
- `autoresearch` shares the same feature set across Claude Code and Codex; on Codex it follows a default sequential execution model with explicit delegation approval.
- All four skills include `agents/openai.yaml` to ship Codex UI metadata alongside the skill.

## License

MIT
