---
name: blueprint
description: Codex용 자동화 에이전트 시스템 설계서 생성 스킬. 사용자 인터뷰로 요구사항을 정리하고 Codex 구현 기준의 통합 설계 문서(.md)를 작성한다. Use when the user asks for "/blueprint", "blueprint", "에이전트 설계", "설계서 만들어", "agentic workflow design", or any request to plan a Codex automation or agent workflow.
metadata:
  short-description: Create a Codex automation blueprint
---

# Blueprint

## Overview

Conduct a short interview about the task the user wants to automate, then produce a single design document `./blueprint-<task-name>.md` based on Codex implementation standards.

- Default assumption: `single Codex agent + skills/scripts as needed`.
- Do not include Claude Code-specific elements such as `.claude/commands`, `.claude/agents`, `AGENT.md`, or `Task`-based sub-agent structures.
- Implementation spec covers structure and responsibilities only — do not write actual code bodies or lengthy prompts.

## Workflow

### 1. Assess Gaps First

Check the four areas below first, and ask only about what is missing.

| Area | Minimum items to confirm |
|---|---|
| Goal and success criteria | What does completion look like, what counts as failure |
| Task procedure | Input, output, branch conditions, human intervention points |
| Execution environment | File formats, APIs, external tools, storage location |
| Constraints | Accuracy, cost, speed, security, permissions, operational scope |

Interview rules:

- Ask at most 3 questions per turn.
- In default mode, ask directly in plain text messages.
- For items the user does not know, apply a reasonable default and state that assumption explicitly in the document.
- Finish within 3 rounds at most; after that, note assumptions and risks and proceed to the writing phase.

### 2. Write the Blueprint

Read the following two reference documents and apply them faithfully.

- `references/document-template.md`
- `references/design-principles.md`

If you want a calibration sample for specificity and decision framing, also skim:

- `references/example-blueprint.md`

**Interview findings → document section mapping (confirm before writing):**

| Interview finding | → Document section |
|---|---|
| Why it is needed, what problem it solves | `## 0. Goals and Deliverables` + `### Background` + `### Objective` |
| What is in / out of scope | `### Out of Scope` + `### Scope` |
| Input format, output format, trigger | `### Inputs` + `### Outputs` + `### End-to-End Flow` |
| Technical constraints, API limits | `### Constraints` |
| Step-by-step processing, branch conditions | `#### Step NN` blocks + `### State Model` |
| Agent judgment vs script processing | `### LLM vs Code Boundary` |
| Tools / APIs used | `### Skill and Script Inventory` |
| Single vs multi-agent | `### Recommended Folder Structure` + `### AGENTS.md Responsibilities` |
| Failure conditions, retry expectations | `#### Step NN` → `7) Failure Handling:` |

Writing rules:

- Final output path: `./blueprint-<task-name>.md` at the project root
- Intermediate artifacts use the `output/stepNN_<name>.<ext>` naming convention
- Every workflow step must include all 9 fields below:
  1. Step Goal
  2. Input / Output
  3. LLM Decision Area
  4. Code Processing Area
  5. Success Criteria
  6. Validation Method
  7. Failure Handling
  8. Skills / Scripts
  9. Intermediate Artifact Rule
- Include all state tokens: `COLLECTING_REQUIREMENTS`, `PLANNING`, `RUNNING_SCRIPT`, `VALIDATING`, `NEEDS_USER_INPUT`, `DONE`, `FAILED`.

### 3. Validate Before Hand-off

After saving the document, run the validation below.

Do not assume a relative path from the target project — run the validation script from the **currently installed blueprint skill path**.

Example (adapt the path to your installation):

```bash
python ~/.codex/skills/blueprint/scripts/validate_blueprint_doc.py ./blueprint-<task-name>.md
# or if installed elsewhere:
# python /path/to/codex/skills/blueprint/scripts/validate_blueprint_doc.py ./blueprint-<task-name>.md
```

- If validation fails, fix the document and run again.
- This validation checks document structure only.
- Use `./.codex/skills/blueprint/scripts/validate_blueprint_doc.py` only when working directly on the skill repository itself (local clone).
- When adding or modifying a Codex skill itself, use the separately installed `skill-creator` skill's `quick_validate.py`.

### 4. Review

Show the user the document path and a brief summary of key decisions, then confirm whether any changes are needed.

## Notes

- Document structure follows English headers from the template — the validation script operates based on those headers.
- Design documents that include skill creation must have a **skill-creator usage requirement** section (see `references/design-principles.md` › "Skill Creation Standards" for exact wording).
- When designing a new skill folder, write paths relative to `.codex/skills/<skill-name>/` and do not create unnecessary files.
