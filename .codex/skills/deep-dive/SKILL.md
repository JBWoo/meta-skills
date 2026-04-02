---
name: deep-dive
description: A Codex skill for in-depth requirements interviews and spec document writing. Conducts multi-round questioning to clarify core behavior, technical constraints, UX, tradeoffs, and failure modes, then writes a new spec or updates an existing document. Use when the user asks for "/deep-dive", "deep dive", "interview me", "create a spec", or wants a structured requirements deep dive in Codex.
metadata:
  short-description: Run a deep requirements interview and spec write-up
---

# Deep Dive

## Overview

Clarifies ambiguous requests through multi-round interviews and organizes the results into a spec document.

- Default output file is `spec-<topic-slug>.md`
- **CRITICAL**: If a related document already exists, you MUST update that document. Creating a new file when an existing document is present is incorrect behavior.
- New file creation is only allowed when no related document exists at all, or when the user explicitly requests `new` before the interview.
- Ask fewer questions, go deeper, and build cumulatively on previous answers.

## Workflow

### 1. Read `$ARGUMENTS`

`$ARGUMENTS` is the text the user typed after the skill trigger. Example: `/deep-dive payment system` → $ARGUMENTS = "payment system". If no argument is given, ask the topic as the first question.

First, identify the topic, intent, and expected output from the user's request.

- Note the key keywords and candidate topic slugs.
- Do not immediately assume whether this is augmenting an existing document or starting a new plan — scan for documents in the next step.

### 2. Scan the Workspace First

Scan the current working directory for existing spec or planning documents first.

- Prefer `rg --files` for file discovery.
- Priority candidate patterns:
  - `blueprint-*.md`
  - `spec-*.md`
  - `*-spec.md`
  - `*blueprint*.md`
  - `*planning*.md`
  - `*requirements*.md`
  - `*PRD*.md`
  - `*기획*.md`
  - `*설계*.md`
  - `architecture.md`, `roadmap.md`, `overview.md`, `notes.md`
  - Always check `CLAUDE.md` and `README.md` regardless of pattern.
- If a related document is found, read it first and summarize each document's purpose and current section structure.
- If a related document is found, prepare to show it to the user before the interview.

### 3. Confirm Update vs New Before Interview

If any related document exists, you MUST get user confirmation before starting the interview. This step exists so the existence of the document is not forgotten during the long interview.

- Use `request_user_input` when available to collect the choice. The default recommendation is always to update the existing document.
- If 1 candidate: ask with two choices — `Update existing (Recommended)` / `Create new`.
- If 2 candidates: set the most likely existing document as the recommendation, with the other candidate or `Create new` as the remaining options.
- If 3+ candidates: include only the top 2 as options, and accept a free-text filename for `Other`.
- Example:

```text
다음 기존 문서를 찾았습니다:
1. `filename.md` — [한 줄 요약]

이 문서를 업데이트할까요? 새 파일을 만들려면 `new`라고 답해주세요.
```

- If the user does not explicitly say `new`, default to updating the existing document.
- The decision made in this step is FINAL. Do not re-evaluate or reverse it in later steps.

### 4. Interview in Rounds

Interview rules:

- Ask only 1–2 questions per round.
- Build deeper on the previous answer.
- Instead of obvious questions, probe for specific operational conditions or edge cases.
- Typically wrap up within 3–5 rounds.

Category priority:

- **If the previous answer opened a thread, dig deeper into that same category first.** Depth beats breadth.
- Add one uncovered category per round as the interview progresses.
- Skip categories that clearly don't apply to the topic (e.g., UX for a non-interactive CLI script).

Category list (1, 5, 6 always included):

1. Core behavior *(always)* — normal flow, edge cases, exit conditions
2. Inputs and outputs — format, source, storage location, validation criteria
3. Technical constraints — stack, external systems, permissions, performance limits
4. UX or operator flow *(skip for non-interactive tools)* — who uses it, when, and how
5. Tradeoffs *(always)* — speed vs. accuracy, simplicity vs. scalability
6. Failure modes *(always)* — input errors, external failures, retry criteria
7. Future change — scale increase, follow-on phases, extension points
8. Concerns — what the user is most worried about

Default mode:

- Conduct general interview questions as assistant messages.
- However, when explicit option selection is needed (e.g., document selection), prefer `request_user_input`.
- Even if an answer is incomplete, do not stop — note any assumptions clearly and continue.

### 5. Follow the Step 3 Decision

Follow the decision made in Step 3 exactly. Do not re-evaluate here.

- DO NOT re-evaluate. Follow the decision from Step 3.
- HARD RULE: If an existing document was found and the user did not explicitly say `new`, you MUST update the existing document.
- New file creation is only allowed when one of the following is true:
  - No related document was found at all.
  - The user explicitly requested `new` in Step 3.

### 5a. Update Existing Document Carefully

Rules when updating an existing document:

- Before editing, you MUST perform the following analysis first:
  1. List every section heading in the existing document.
  2. Map each interview finding to the section it belongs in.
  3. Classify each item as `APPEND` / `REVISE` / `NEW_SECTION`.
- Merge rules:
  - `APPEND`: Add at the end of the matching section.
  - `REVISE`: Keep the existing content and update only what is necessary — do not leave inline markers at the change point.
  - `NEW_SECTION`: Add at the end of the document; if `Open Questions` exists, insert before it.
- Do NOT modify, delete, reorder, or reformat any existing content that was not covered in the interview.
- Do not touch unrelated content.
- If interview results conflict with existing content, replace the existing content directly. Do not leave inline markers (e.g., `> ⚠️ Updated:`). A spec document should show the current state; change history is tracked in git log.
- Perform actual file edits using section-level `apply_patch`.
- Do NOT work around this step by creating a new file even when an existing document is present.

### 5b. Create a New Spec Only When Allowed

Only reach this step when one of the following is true.

```markdown
> ⚠️ Only reach this step if: (a) no existing document was found, OR (b) user explicitly requested a new file.
> If neither condition is true, STOP and go back to Step 5a.
```

Default structure for a new document:

```markdown
# Spec: [Topic]

## Overview
[1-2 sentence summary]

## Goals
- ...

## Requirements
### Functional
- ...
### Non-functional
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

At the end, briefly report only the following.

- The path of the file updated or created.
- The key decisions clarified through this interview.
- Any remaining uncertainties.
