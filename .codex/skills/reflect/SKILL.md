---
name: reflect
description: A skill for wrapping up a Codex work session. Summarizes changes made this session, identifies doc update points, automation ideas, learnings, and next actions all at once. Use when the user asks for "/reflect", "reflect", "session reflect", "end session", or wants a Codex session wrap-up.
metadata:
  short-description: Summarize a Codex session and next actions
---

# Reflect

## Overview

Wrap up a Codex session by summarizing changes and follow-up actions.

- Do not replicate the Claude Code `Task`-based parallel subagent flow
- Investigate files and changes directly within Codex, and integrate results yourself
- Default behavior is `report first, edit only when needed`

## Workflow

### 1. Inspect Session State

Start by briefly summarizing the current state:

- Current workspace file structure
- Files created or modified in this session
- Scope of changes shown by `git status --short` or a relevant diff
- Presence of key documents (`README.md`, `AGENTS.md`, recent spec/design docs)

Compress this information into a one- or two-sentence `PROJECT_STATE` to use as an internal reference.

### 2. Produce Four Analyses

Check all four categories below:

1. Docs to update
   - Which documents do not yet reflect the actual changes made
2. Automation ideas
   - Which repetitive tasks could be extracted as a skill, script, or hook
3. Learnings
   - New patterns, constraints, or tool usage confirmed in this session
4. Next actions
   - 1–3 immediate follow-up tasks to continue right now

Rules:

- Base entries only on what was actually done
- Merge duplicate items into one
- Discard items with low importance or low actionability

### 3. Decide Whether to Apply Changes

If the user explicitly wants doc updates applied, apply them immediately.

Otherwise, show the summary first and confirm in one sentence which follow-up actions to take:

- 문서 반영
- 자동화 아이디어 기록
- 학습 노트 기록
- 요약만 제공

### 4. Apply Updates Carefully

Rules for follow-up edits:

- If an existing document is relevant, update it in place
- Do not create unrelated documents
- Use `apply_patch` for file modifications

**When saving learning records:** Append to `~/.codex/learnings.md` in the format below (create the file if it doesn't exist).

```markdown
## YYYY-MM-DD — [project name]
- [개념/도구/패턴]: [한 줄 설명]
- [개념/도구/패턴]: [한 줄 설명]
```

**When creating automations:** For skills, create `.codex/skills/<name>/SKILL.md` and use `skill-creator` if available. For scripts, create `.codex/scripts/<name>.py`.

### 5. Final Output Format

Present results concisely in this order:

1. Session summary
2. Docs to update
3. Automation ideas
4. Learnings
5. Next actions

If any files were modified, include the file paths alongside the output.

## Notes

- When running this skill in Codex, do not assume a separate subagent or a dedicated `AskUserQuestion` tool is available.
- Bundle only the necessary parallel read operations with `multi_tool_use.parallel`; handle all judgment and integration in the main flow.
