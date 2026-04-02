---
name: reflect
description: A skill for wrapping up a Codex work session. Summarizes changes made this session, identifies doc update points, automation ideas, learnings, and next actions all at once. Use when the user asks for "/reflect", "reflect", "session reflect", "end session", "세션 정리", "오늘 한 거 정리", or "마무리", or wants a Codex session wrap-up after substantial work.
metadata:
  short-description: Summarize a Codex session and next actions
---

# Reflect

## Overview

Wrap up a Codex work session by inspecting what actually changed, extracting the highest-signal follow-ups, and then optionally applying selected updates.

- Do not replicate Claude Code `Task`-based subagent orchestration
- Investigate files and diffs directly in the current agent
- Use `multi_tool_use.parallel` only for independent reads
- Default behavior is `report first, edit only when useful`

## Workflow

### 1. Inspect Session State

Collect concrete session evidence first:

- Current workspace structure
- Files created or modified in this session
- Scope of changes from `git status --short` and a relevant diff
- Presence of key documents such as `README.md`, `AGENTS.md`, recent specs, or blueprints

Compress this into a short internal `PROJECT_STATE` summary before moving on.

### 2. Produce Four Analyses

Analyze the session in four categories:

1. Docs to update
   - Which docs no longer reflect the implemented behavior
2. Automation ideas
   - Which repeated manual steps could become a skill, script, or hook
3. Learnings
   - What new constraints, techniques, or patterns became clear
4. Next actions
   - The 1-3 most immediate follow-up tasks with the best payoff

Rules:

- Base items only on actual work performed
- Merge duplicates across categories
- Drop low-value or vague items
- Keep outputs concise and actionable

### 3. Present Summary and Ask What to Apply

Report the four analysis buckets first.

If the user explicitly asked to apply updates, do so immediately.

Otherwise ask which action(s) to take next. Prefer `request_user_input` when there are real choices to make.

Possible actions:

- `문서 반영`
- `자동화 아이디어 기록`
- `학습 기록 저장`
- `요약만 제공`

Only show actions that are actually available, except `요약만 제공`, which is always valid.

### 4. Apply Follow-up Changes Carefully

Rules for edits:

- If an existing document is relevant, update it in place
- Do not create unrelated files
- Use `apply_patch` for modifications
- Keep changes narrow and directly tied to the session

#### 4a. Docs to update

- Update the smallest relevant existing document
- Append or revise only the sections justified by the session
- Do not rewrite unrelated sections

#### 4b. Automation ideas

For each accepted automation:

- Skill -> create `.codex/skills/<name>/SKILL.md`
- Script -> create `scripts/<name>.py`
- If `skill-creator` is available and the user wants a real skill scaffold, use it; otherwise create the minimal required structure

Keep automation suggestions narrow. Do not overbuild.

#### 4c. Learnings

Append to `~/.codex/learnings.md` (create it if missing) in this format:

```markdown
## YYYY-MM-DD - [project name]
- [concept/tool/pattern]: [one-line explanation]
- [concept/tool/pattern]: [one-line explanation]
```

### 5. Final Output Format

Present results in this order:

1. Session summary
2. Docs to update
3. Automation ideas
4. Learnings
5. Next actions

If any files were modified, include the file paths.

## Notes

- This skill is useful after substantial implementation work, not short Q&A
- Prefer concrete evidence from the repo over memory or vague recap
- Reflection quality depends on selecting only high-signal items, not producing a long checklist
