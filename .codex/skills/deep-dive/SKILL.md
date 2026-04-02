---
name: deep-dive
description: A Codex skill for in-depth requirements interviews and spec document writing. Conducts multi-round questioning to clarify core behavior, technical constraints, UX, tradeoffs, and failure modes, then writes a new spec or updates an existing document. Use when the user asks for "/deep-dive", "deep dive", "interview me", "create a spec", "요구사항 정리", "기획서 만들어", or "스펙 작성", or when they have a rough idea and need a structured requirements deep dive in Codex.
metadata:
  short-description: Run a deep requirements interview and spec write-up
---

# Deep Dive

## Overview

Clarify ambiguous work through a focused, multi-round interview, then update an existing spec when possible or create a new one when needed.

- Default output file: `spec-<topic-slug>.md`
- **CRITICAL**: If a related document already exists, update that document unless the user explicitly asks for `new`
- Ask fewer questions, go deeper, and build cumulatively on prior answers
- Prefer targeted edits with `apply_patch`; do not overwrite unrelated content

## Workflow

### 1. Read `$ARGUMENTS`

`$ARGUMENTS` is the text after the skill trigger. Example: `/deep-dive payment system` -> `$ARGUMENTS = "payment system"`.

- If no argument is given, ask the topic as the first question
- Extract the likely topic, intent, and expected deliverable
- Do not decide update-vs-new yet; scan the workspace first

### 2. Scan the Workspace First

Search the current working directory for existing spec or planning documents before interviewing.

- Prefer `rg --files`
- Check candidate patterns:
  - `spec-*.md`
  - `*-spec.md`
  - `blueprint-*.md`
  - `*blueprint*.md`
  - `*planning*.md`
  - `*requirements*.md`
  - `*PRD*.md`
  - `*기획*.md`
  - `*설계*.md`
  - `architecture.md`, `roadmap.md`, `overview.md`, `notes.md`
- Always inspect `README.md` and `AGENTS.md` if present
- If a related document is found, read it and summarize:
  - its purpose
  - current section structure
  - how directly it matches the requested topic

### 3. Confirm Update vs New Before Interview

If any related document exists, confirm the target before starting the long interview.

- Use `request_user_input` when it meaningfully reduces ambiguity
- Default recommendation is always to update the most relevant existing document
- If exactly 1 strong candidate exists: ask `Update existing (Recommended)` vs `Create new`
- If multiple candidates exist: recommend the best match, expose the next best option, and allow free-text if needed
- If the user does not explicitly say `new`, default to updating the existing document
- This decision is final for the rest of the run

### 4. Interview in Rounds

Interview rules:

- Ask only 1-2 questions per round
- Build deeper on the previous answer before broadening
- Avoid generic prompts like "what is the goal?" when you can ask a sharper operational question
- Usually finish within 3-5 rounds
- If the user says "모르겠다" or "알아서", choose a reasonable default, state it clearly, and keep going

Category coverage:

1. Core behavior *(always)* — happy path, edge cases, completion condition
2. Inputs and outputs — format, source, destination, validation
3. Technical constraints — stack, APIs, permissions, performance limits
4. UX or operator flow *(skip if not applicable)* — who uses it, when, how
5. Tradeoffs *(always)* — speed vs accuracy, simplicity vs flexibility
6. Failure modes *(always)* — retries, escalation, abort conditions
7. Future change — likely extensions or scale changes
8. Concerns — what would make the user reject the result

Default mode guidance:

- Ask directly in assistant messages unless structured option selection is needed
- Prefer `request_user_input` for explicit branching choices such as document selection
- Even if an answer is incomplete, continue and mark assumptions clearly

### 5. Follow the Decision Exactly

Do not re-evaluate update-vs-new later.

- If an existing document was found and the user did not explicitly request `new`, you MUST update it
- New file creation is allowed only when:
  - no related document was found at all, or
  - the user explicitly requested `new`

### 5a. Update Existing Document Carefully

Before editing, perform this merge analysis:

1. List every section heading in the existing document
2. Map each interview finding to the section it belongs in
3. Classify each mapped item as `APPEND`, `REVISE`, or `NEW_SECTION`

Merge rules:

- `APPEND`: add at the end of the matching section
- `REVISE`: replace outdated content directly; do not leave change markers
- `NEW_SECTION`: append at the end, or place before `Open Questions` if that section exists
- Leave unrelated content exactly as-is
- Do not reformat untouched sections
- Use section-level `apply_patch`; do not replace the whole file unless the file is clearly a throwaway draft

If interview findings contradict old content, the spec should reflect the current truth. Git history captures the change history; the doc should not.

### 5b. Create a New Spec Only When Allowed

Only create a new file when step 5 allows it.

Filename:

- `spec-<topic-slug>.md` in the current working directory

Default structure:

```markdown
# Spec: [Topic]

## Overview
[1-2 sentence summary]

## Goals
- ...

## Scope
- In:
- Out:

## Inputs and Outputs
- ...

## Requirements
- ...

## Technical Notes
- ...

## UX / Operator Flow
- ...

## Tradeoffs and Decisions
- ...

## Failure Modes
- ...

## Open Questions
- ...
```

### 6. Hand-off

At the end, report only:

- the file path created or updated
- the key decisions clarified through the interview
- any remaining uncertainties or assumptions

## Notes

- Update existing documents by default; creating a separate file when a good target already exists is incorrect behavior
- Depth matters more than exhausting every category mechanically
- The finished document should describe the current intended behavior cleanly, not narrate what changed
