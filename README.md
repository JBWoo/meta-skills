# Jangpm Meta Skills for Claude Code and Codex

A collection of meta skills for designing agent systems, clarifying requirements, wrapping up sessions, and automatically optimizing skills.

- Claude Code distribution: `.claude/`
- Codex distribution: `.codex/skills/`

## Skills

| Skill | Role | Claude Code | Codex |
|---|---|---|---|
| `blueprint` | Design document for automation/agent systems — includes a structural validation script | `blueprint` skill | `blueprint` 또는 `$blueprint` |
| `deep-dive` | Multi-round interview to produce a detailed spec document | `deep-dive` skill | `deep-dive` 또는 `$deep-dive` |
| `reflect` | Summarize a work session, identify doc update points, surface next actions | `reflect` skill | `reflect` 또는 `$reflect` |
| `autoresearch` | Automated skill optimization (iterative runs + evaluation + prompt mutation) — outputs improved skill, `results.json`, `changelog.md`, and a live HTML dashboard | `autoresearch` skill | `autoresearch` 또는 `$autoresearch` |

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
  skills/
    autoresearch/
      SKILL.md
      references/
        dashboard-guide.md     # Live HTML dashboard during runs
        eval-guide.md          # Writing binary + comparative evals
        execution-guide.md     # Run loop mechanics
        logging-guide.md       # results.json / results.tsv schema
        mutation-guide.md      # Prompt mutation strategies
        pipeline-guide.md      # Full pipeline overview
        worked-example.md      # Annotated end-to-end example
    blueprint/
      SKILL.md
      references/
        document-template.md   # Output document section-by-section template
        design-principles.md   # Agent structure and design rules
        example-blueprint.md   # Fully annotated sample blueprint
      scripts/
        validate_blueprint_doc.py  # Structural validation for blueprint docs
    deep-dive/
      SKILL.md
    reflect/
      SKILL.md

.codex/
  skills/
    autoresearch/
      SKILL.md
      agents/openai.yaml       # Codex UI metadata
      references/              # (same as Claude Code)
    blueprint/
      SKILL.md
      agents/openai.yaml
      references/
      scripts/
    deep-dive/
      SKILL.md
      agents/openai.yaml
    reflect/
      SKILL.md
      agents/openai.yaml
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
```

### macOS / Linux

```bash
cp -r ./.claude/skills/autoresearch ~/.claude/skills/
cp -r ./.claude/skills/blueprint    ~/.claude/skills/
cp -r ./.claude/skills/deep-dive    ~/.claude/skills/
cp -r ./.claude/skills/reflect      ~/.claude/skills/
```

## Codex vs Claude Code differences

- This repository ships both distributions as skill folders centered on `SKILL.md`; it does not include separate Claude `/commands` wrapper files.
- Updated `.claude/...` paths, `Task`-based subagents, and `AskUserQuestion` assumptions to fit the Codex flow.
- `blueprint` includes a Codex-compatible document template, design principles, and a structure validation script.
- `autoresearch` shares the same feature set across Claude Code and Codex; on Codex it follows a default sequential execution model with explicit delegation approval.
- The Codex distribution includes `agents/openai.yaml` files to ship Codex UI metadata alongside each skill.

## License

MIT
