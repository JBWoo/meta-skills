# Design Principles for Agentic Systems

## Folder Structure

```
/project-root
  ├── CLAUDE.md                        # Main agent instructions
  ├── /.claude
  │   ├── /skills/<skill-name>
  │   │   ├── SKILL.md
  │   │   ├── /scripts                 # Deterministic tools
  │   │   └── /references              # (optional) domain knowledge, API guides
  │   └── /agents/<subagent-name>
  │       └── AGENT.md
  ├── /output                          # Artifacts
  └── /docs                            # (optional) reference documents
```

## Agent vs Script Responsibility

| Agent handles directly | Script handles |
|------------------------|----------------|
| Classification, decision-making, priority judgment | File I/O, data parsing |
| Quality evaluation, qualitative analysis | External API calls |
| Context-based inference | Iteration, aggregation |
| Natural language generation/summarization | Static analysis, test execution |

## Validation Patterns

Every workflow step must define success criteria. Choose validation type by output nature:

| Validation type | Applies to | Example |
|-----------------|-----------|---------|
| **Schema validation** | Structured outputs | Required fields present, type check |
| **Rule-based** | Quantitative criteria | Item count, character count, required sections |
| **LLM self-validation** | Qualitative outputs | Summary quality, tone, completeness |
| **Human review** | High-risk final outputs | External documents, decisions |

## Failure Handling

| Pattern | When to use |
|---------|-------------|
| **Auto retry** | Validation failure is simple omission/format error (specify max retries) |
| **Escalation** | High judgment uncertainty or ambiguous criteria → ask human |
| **Skip + log** | Optional step with no flow impact → record reason in log |

## Agent Structure Choice

**Single agent** (default):
- Workflow is simple and instructions are short

**Sub-agent separation** (when needed):
- Context window optimization required — instructions too long to always load
- Clearly distinct independent task blocks requiring different domain knowledge

## Sub-agent Design Rules

- CLAUDE.md (main agent) acts as orchestrator
- Sub-agents must NOT call each other directly — coordinate through main
- AGENT.md must specify: role, trigger condition, input/output, referenced skills

## Data Transfer Patterns

| Pattern | When to use |
|---------|------------|
| **File-based** | Data is large or structured → `/output/step1_result.json` |
| **Prompt inline** | Data is small and simple |

Recommendation: Store intermediate outputs in `/output/` and pass only file paths.

## Skill vs Sub-agent

| Skill | Sub-agent |
|-------|-----------|
| Tool/function unit (small) | Role/responsibility unit (large) |
| Shareable across multiple agents | Specific to one workflow |
| Examples: `file-parser`, `api-caller` | Examples: `code-reviewer`, `report-generator` |
