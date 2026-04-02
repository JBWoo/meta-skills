---
name: autoresearch
description: Autonomously optimize any Codex skill by running it repeatedly, scoring outputs against evals (binary for rules + comparative for quality), mutating the skill's prompt and reference assets, and keeping improvements. Based on Karpathy's autoresearch methodology. Use this skill whenever the user mentions optimizing a skill, improving a skill, running autoresearch, making a skill better, self-improving a skill, benchmarking a skill, evaluating a skill, running evals on a skill, or any request to iteratively test and refine a skill — even if they don't use the word "autoresearch" explicitly. Also trigger on 스킬 개선, 스킬 최적화, 스킬 벤치마크, 스킬 평가. Outputs an improved SKILL.md, a results log, a changelog, and a research log of meaningful direction shifts.
---

# Autoresearch for Skills

Most skills work about 70% of the time. The other 30% you get garbage. The fix isn't to rewrite the skill from scratch. It's to let an agent run it dozens of times, score every output, and tighten the prompt until that 30% disappears.

This skill adapts Andrej Karpathy's autoresearch methodology (autonomous experimentation loops) to Codex skills. Instead of optimizing ML training code, we optimize skill prompts.

---

## the core job

Take any existing skill, define what "good output" looks like as eval checks, then run a loop that:

1. Generates outputs from the skill using test inputs
2. Scores every output against the eval criteria (binary checks for rules + comparative checks for quality)
3. Mutates the skill — not just the prompt text, but also reference files, templates, and design assets
4. Keeps mutations that improve the score, discards the rest
5. Repeats until the score ceiling is hit or the user stops it

**Output:** An improved SKILL.md + `results.tsv` log + `changelog.md` of every mutation attempted + `research-log.json` of meaningful direction shifts + a live HTML dashboard.

---

## before starting: gather context

Codex should not block on a perfect spec. Gather the minimum viable experiment contract, then start.

1. **Target skill(s)** — Which skill to optimize? (exact path to SKILL.md). For pipelines, list all skills in execution order.
2. **Pipeline mode** — Single skill or multi-skill pipeline? Default: single. See `references/pipeline-guide.md` for pipeline details.
3. **Test inputs** — 3-5 different prompts/scenarios. If the user did not provide them, draft a starter set yourself and state the assumption.
4. **Eval criteria** — Binary checks for rules (3-6) + comparative checks for quality dimensions (0-5). If the user did not provide them, propose a starter eval suite and tighten it after baseline. See `references/eval-guide.md`.
5. **Runs per experiment** — Default: 3 for light skills, 1-2 for heavy skills, 5 only when the run is cheap.
6. **Budget cap** — Optional. Default: 5 total experiments in one Codex turn unless the user explicitly wants a longer run.
7. **Termination conditions** — Default: stop when budget cap is reached, or when 95%+ is sustained for 3 consecutive accepted experiments.
8. **Human review mode** — Default: ask for review after baseline and after the first meaningful keep. Set to `skip` only when the user explicitly wants unattended auto mode.
9. **Execution mode** — Default: sequential in the current agent. Use subagents or delegated runs only if the user explicitly asks for delegation, parallel agent work, or subagents.
10. **Run harness** — Define the exact repeatable command or workflow that constitutes "running the target skill". If no reliable harness exists, your first job is to build a lightweight harness before claiming autoresearch is active.

If the user provides an `evals.json` file, use that instead of drafting items 3-4.

**Execution mode rules:**
- Use `sequential` by default.
- Do not spawn subagents just because they might be faster; Codex requires explicit user permission for delegation.
- Treat "run the skill" as an explicit, repeatable harness. A conversational skill is not executable until you define how prompts, outputs, and artifacts are captured.
- If fresh runs are unavailable, continue sequentially and note the risk of context contamination in the log.

---

## step 1: read the skill

Before changing anything, read and understand the target skill completely.

1. Read the full SKILL.md file
2. Read any files in `references/` that the skill links to
3. Identify the skill's core job, process steps, and output format
4. Note any existing quality checks or anti-patterns already in the skill
5. If the target is a Codex skill and `agents/openai.yaml` exists, read it and check whether the UI metadata still matches the skill's actual purpose

Do NOT skip this. You need to understand what the skill does before you can improve it.

For **pipeline mode**, read `references/pipeline-guide.md` and map the full data flow across all skills.

---

## step 2: build the eval suite

Convert the user's eval criteria into a structured test. See `references/eval-guide.md` for full templates, examples, and the assertion taxonomy.

**Three eval types:**

- **Binary evals** — objective rule compliance (yes/no). Use for hard rules.
- **Comparative evals** — subjective quality improvement. Judge whether a mutation improved quality along a specific dimension (win=1, tie=0.5, loss=0). Every skill should have at least 1-2 comparative evals alongside binary checks — binary alone plateaus quickly.
- **Fidelity evals** — pipeline stage consistency (pipeline mode only). See `references/pipeline-guide.md`.

**Scoring:** Binary: pass=1, fail=0. Comparative: win=1, tie=0.5, loss=0. Fidelity: pass=1, fail=0. Total = sum of all. `max_score = total assertions x runs per experiment`.

### Eval type hierarchy (ordered by determinism)

When writing evals, use the highest tier possible. LLM-as-judge is a last resort.

**Tier 1 — Deterministic checks (first choice)**
grep, regex, file existence, JSON/YAML parse success, character count range, required section presence, etc.
Same input → always same result. Most reliable.

Examples:
- "Does the output have a ## 요약 section?" → `grep -q "^## 요약" output.md`
- "Is it valid JSON?" → `python -c "import json; json.load(open('output.json'))"`
- "Is it between 500 and 2000 characters?" → `wc -c output.txt | awk '{exit ($1<500 || $1>2000)}'`

**Tier 2 — Structural validation**
Programmatically verify structural properties of the output. Requires some parsing logic but is still deterministic.

Examples:
- Do markdown headings follow the correct hierarchy? (H1 → H2 → H3)
- Does the table have the same column count across all rows?
- Do code blocks have a language specifier?

**Tier 3 — LLM-as-judge (last resort)**
Use only for items that cannot be verified programmatically — content quality, tone, accuracy.

**Goal: at least 50% of all evals should be Tier 1-2.** An eval suite built entirely on Tier 3 has too much noise to reliably detect the effect of mutations.

### Rules for all evals

- Specific enough to be consistent. "Is the text readable?" is too vague. "Are all words spelled correctly with no truncated sentences?" is testable.
- Not so narrow that the skill games the eval.
- Each eval should test something distinct — no overlapping checks.

**Before finalizing, run the 3-question test on each eval:**

1. Could two different agents score the same output and agree? (if not → tighten)
2. Could a skill game this eval without actually improving? (if yes → too narrow)
3. Does this eval test something the user actually cares about? (if not → drop it)

---

## step 3: generate the live dashboard

Before running any experiments, create `autoresearch-[skill-name]/dashboard.html` and open it. See `references/dashboard-guide.md` for the full dashboard spec.

**Key rule:** Do not fetch results.json — instead, after each experiment, inline the data directly into `<script>const RESULTS_DATA = ...;</script>` inside dashboard.html. This lets you open it with the `file://` protocol without needing a separate server.

---

## how to run the target skill

Each experiment requires a repeatable run harness that executes the target skill and collects its outputs. In Codex, do not hand-wave this step.

Acceptable harnesses:

- A local script or command that runs the workflow end-to-end
- A bounded manual protocol with fixed prompt, fixed output path, and deterministic artifact capture
- A delegated subagent task only when the user explicitly approved delegation

Before baseline, write down the harness in the run folder so later experiments are comparable. If you cannot define a harness, stop calling the process autoresearch and switch to "skill rewrite + manual review" mode instead.

---

## step 4: establish baseline

If `autoresearch-[skill-name]/` already exists, skip baseline creation and jump to `resuming a previous run`.

Run the skill AS-IS before changing anything. This is experiment #0.

1. Create working directory: `autoresearch-[skill-name]/` with `runs/baseline/` subdirectory
2. Create `results.json`, `results.tsv`, `changelog.md`, `research-log.json`, and `dashboard.html`, then open the dashboard
3. Back up the original SKILL.md as `SKILL.md.baseline`
4. Run the skill using the test inputs
5. **Copy all outputs into `runs/baseline/<prompt-id>/`** — every artifact the skill produces must be preserved
6. Score every output against every eval
7. Record the baseline score and update results.json
8. Create a git branch: `git checkout -b autoresearch/[skill-name]` (if already exists, use `autoresearch/[skill-name]-N`)
9. Add log files to `.gitignore`: the entire `autoresearch-[skill-name]/` directory. Logs must accumulate independently of experiment rollbacks.
10. Commit the baseline SKILL.md as the first commit: `git add SKILL.md && git commit -m "autoresearch: baseline ([score]/[max])"`
11. Write `run-harness.md`. Record the exact commands used in experiments, the prompt set, output capture rules, and any known limitations.

**IMPORTANT:** After establishing baseline, choose one of two modes explicitly:

- `interactive`: report baseline and wait for user approval before continuing
- `unattended`: continue until budget cap or stop conditions are hit, then report the full batch

Default to `interactive` unless the user explicitly asked for unattended looping.

For prompt rotation strategy and heavy pipeline adaptation, see `references/pipeline-guide.md`.

---

## step 5: human review phase (optional)

> Skip this step entirely if the user set human review mode to `skip`.

In Codex, human review is usually front-loaded but bounded. By default, review baseline plus the first meaningful keep. Expand to 2-3 reviewed experiments only when the skill has strong subjective quality dimensions.

This is where subjective judgment — tone, aesthetic sense, brand fit, personal preference — gets baked into the optimization direction before any unattended batch takes over.

**For each human-reviewed experiment:**

1. **Analyze failures** and form a hypothesis (same as step 6)
2. **Make ONE bounded change** to the selected target files (usually `SKILL.md`; use a single linked reference file only when L2 is the active hypothesis)
3. **Commit the change:** `git add <mutated-files> && git commit -m "autoresearch: [one-line description]"`
4. **Run the experiment** and score it
5. **Present results** showing: the change and why, before/after score, 2-3 sample outputs, keep/discard recommendation
6. **Ask the user:** "Does this direction feel right?" / "Anything the evals aren't catching?"
7. **If subjective feedback is given**, note it in changelog.md as `[HUMAN INSIGHT]` and incorporate into SKILL.md. Do NOT add it as a new eval.
8. **Keep or discard** (same rules as step 6). DISCARD → use the checkpointed rollback flow from step 6.
9. **Log the result** with status `human-reviewed`.

**After the reviewed experiments (or "go auto"):** Switch to auto mode only if the user explicitly allowed unattended looping. Otherwise keep running in small batches and report after each accepted experiment.

---

## step 6: run the autonomous experiment loop

This is the core autoresearch loop. In Codex, autonomy is batch-based, not magical.

Run unattended only when all of the following are true:

- The user explicitly asked for unattended auto mode
- A reliable run harness exists
- Rollback is safe for the touched files
- Budget cap and stop conditions are written down

Otherwise run a bounded batch, report results, and continue in the next turn if needed.

**LOOP:**

1. **Analyze failures.** Look at which evals fail most. Read the actual failing outputs. Identify the pattern.

2. **Form a hypothesis.** Pick a mutation at the right level. See `references/mutation-guide.md` for the three mutation levels (L1: prompt rules, L2: reference assets, L3: eval calibration), good/bad mutation examples, bundled mutations, and L1→L2 transition signals.

3. **Make the change.** Edit the target file(s) at the chosen mutation level.
   - Before editing, checkpoint only the files you plan to touch in this experiment (`SKILL.md`, linked `references/`, and `agents/openai.yaml` if relevant), and record whether each file existed before the experiment.
   - If the target is a Codex skill, update `agents/openai.yaml` only when an accepted mutation changes the skill's user-facing purpose, description, or default invocation text.

4. **Commit the change:** `git add <mutated-files> && git commit -m "autoresearch: [one-line description]"`

5. **Run the experiment.** Execute the skill with the test inputs. **Save all outputs into `runs/exp-N/`** — copy or move every artifact the skill produces into `runs/exp-N/<prompt-id>/` so every experiment is self-contained and comparable.

6. **Score it.** Run every output through every eval. Calculate total score. Measure `skill_lines` with `wc -l SKILL.md`.

7. **Decide: keep or discard.**

   Consider line count changes in SKILL.md alongside the score:

   | Score change | Line count change | Decision |
   |-----------|-----------|------|
   | Improved (+2 or more) | Increased | **KEEP** — meaningful improvement justifies added complexity |
   | Marginal improvement (+1) | Increased by 10+ lines | **DISCARD** — not enough improvement for the added complexity |
   | Same (±0) | Decreased | **KEEP** — same performance with a shorter prompt |
   | Same (±0) | Increased | **DISCARD** — complexity grew with no benefit |
   | Worse | Any | **DISCARD** |

   When two versions have the same score, always prefer the shorter one.

   - **KEEP** → keep this commit. It is the new baseline.
   - **DISCARD** → use a non-destructive rollback: `git reset --soft HEAD~1`, restore only the checkpointed files to their pre-experiment contents, then `git add -A -- <mutated-files>` to realign the index and worktree.

   **Individual eval regression detection:** Even if the total score goes up, strongly consider DISCARD if an eval that previously passed now fails. A gain in one area that hides a regression in another degrades the skill's long-term quality.

8. **Log the result** and update results.json / dashboard.

9. **If this was a direction-level change**, log it in research-log.json (see step 7).

10. **Repeat.** Go back to step 1 until the current batch budget is exhausted or a stop condition is hit.

### Mutation safety rules (with git ratcheting)

- Each mutation is committed before the experiment runs: `git add <mutated-files> && git commit -m "autoresearch: [description]"`.
- KEEP → the commit stays. This is the new baseline.
- DISCARD → `git reset --soft HEAD~1`, then restore only the checkpointed files to their pre-experiment state. If a file was clean before the experiment, `git restore --source=HEAD --staged --worktree -- <path>` is acceptable after the soft reset. If it already had local changes, restore from the checkpoint copy instead of `HEAD`.
- Never use broad repo resets, `git reset --hard`, or commands that revert unrelated user changes.
- If the target repo is already dirty, record which files were pre-modified before the run and exclude them from discard logic unless this experiment changed them.
- The result is a clean linear git history where every surviving commit is a score improvement.

### Periodic deletion experiments

Every 5th experiment, intentionally attempt a "deletion mutation." Find recently added rules that are not actually contributing to the score and remove them. If the score holds after removing a rule, that is the best possible experiment result. If SKILL.md has grown to more than 200% of its baseline size, record a warning in the changelog.

### stop conditions

- The user manually stops you
- Budget cap reached
- 95%+ pass rate for 3 consecutive experiments (or custom termination conditions — see `references/mutation-guide.md`)
- System-level timeout or resource limit
- The run harness is no longer trustworthy (tool drift, missing dependency, target skill changed externally)

Running out of ideas is not a reason to stop → see the "when stuck" strategies below.

### when stuck — strategies specific to skill prompt optimization

After 3 consecutive discards or when ideas run dry:

1. **Reorder instructions**: Move the instruction most related to the most frequently failing eval to the top of SKILL.md. LLMs tend to follow instructions near the start of the prompt more strongly.
2. **Negative → positive framing**: Convert "do not X" into "always do Y." Example: "do not number the list" → "start every list item with a bullet (•)"
3. **Replace examples**: Instead of adding new examples, replace existing ones with examples that directly address the failure pattern. Do not increase the total number of examples.
4. **Deletion experiment**: Remove one instruction and measure the score. If two instructions conflict, removing one is itself an improvement.
5. **Increase specificity**: Add concrete numbers or formats to vague instructions. Example: "write concisely" → "limit each section to 3-5 sentences"
6. **Adjust the persona**: Change the role description at the top of the skill. Example: "You are a professional technical writer" → "You are a technical guide writer for non-developers"
7. **Combine previous near-misses**: Apply two mutations from the changelog that were each discarded but scored close to baseline — simultaneously. (This is the one exception to the "one change at a time" rule.)

---

## step 7: maintain the logs

Three files, three different jobs. Keep them separate. See `references/logging-guide.md` for templates and schemas.

- **changelog.md** — every experiment, kept or discarded. Score, change, reasoning, result, failing outputs, human insight.
- **research-log.json** — direction shifts only. Survives model upgrades. If exceeds 30 entries, keep 10 most recent + pattern summary.
- **results.tsv** — tab-separated, one row per experiment. Columns: `experiment	score	max_score	pass_rate	skill_lines	status	description`. Powers the dashboard.

---

## step 8: deliver results

When the user returns or the loop stops, present:

1. **Score summary:** Baseline → Final (percent improvement)
2. **Total experiments:** How many mutations tried
3. **Keep rate:** Kept vs discarded
4. **Top 3 changes that helped most** (from changelog)
5. **Human insights incorporated** (from the review phase, if any)
6. **Remaining failure patterns** (what still fails, if anything)
7. **Direction shifts** (from research-log.json)
8. **Prompt size change:** baseline SKILL.md line count → final SKILL.md line count
9. **The improved SKILL.md** (already saved in place)
10. **File locations** for all output files
11. **Git log:** `git log --oneline autoresearch/[skill-name]` — history of all accepted mutations

---

## step 9: next steps

autoresearch is not a one-time event — it is a continuous improvement system.

**1 week later: real-world validation**
Check the output quality of the improved skill in actual use. If eval scores are high but real outputs fall short of expectations, the eval criteria are wrong.
→ Fix the evals and restart from a new baseline.

**When upgrading the model: continue optimization**
When a new model is available, reference changelog.md and results.tsv to continue optimizing from where the previous model left off:

```
이 스킬의 autoresearch 기록이 있습니다.
changelog.md에 [N]번의 실험이 기록되어 있고,
최종 pass rate는 [X]%입니다.
이 지점부터 계속 최적화해주세요.
```

**When changing the skill structure: re-establish baseline**
If you significantly changed the structure of SKILL.md or added/removed references/ files, archive the existing autoresearch folder and start from a new baseline. Use the previous changelog as reference for what directions worked.

**Periodic review (recommended monthly)**
Review the patterns in changelog.md:
- If the same type of mutation is repeatedly discarded → change the approach itself
- If deletion experiments keep getting KEEP → signal that the skill is bloating
- If the last 5 experiments all scored ±0 → time to re-examine the eval criteria

---

## step 10: false positive tracking (outer loop)

If eval score is high but actual output quality is low, that is a false positive. Run a monthly review after 10+ real-world outputs have accumulated. See `references/eval-guide.md` (false positive tracking section) for the full process.

---

## output format

```
autoresearch-[skill-name]/
├── dashboard.html          # live browser dashboard (inline data, no server needed)
├── results.json            # data file (also inlined into dashboard)
├── results.tsv             # raw score log with skill_lines column
├── changelog.md            # detailed log of every mutation
├── research-log.json       # direction shifts and strategic patterns only
├── SKILL.md.baseline       # original skill before optimization
├── run-harness.md          # exact execution protocol used for every run
└── runs/                   # one folder per experiment
    ├── baseline/
    ├── exp-1/
    └── exp-N/
```

Plus the improved SKILL.md saved back to its original location.
The git branch `autoresearch/[skill-name]` retains a linear history of all accepted mutations.

---

## worked example

For a concrete walkthrough of 5 experiments (git ratcheting, skill_lines, simplicity decisions, deletion experiments, and mixed Tier 1/2/3 evals), see `references/worked-example.md`.

---

## resuming a previous run

If `autoresearch-[skill-name]/` already exists, do NOT create a new folder or re-establish baseline. Continue from the previous run:

1. Read `changelog.md` and `research-log.json` to understand what was already tried
2. Load `results.json` to find the current best score and next experiment number
3. Read `SKILL.md.baseline` to understand the original starting point
4. If autoresearch branch exists, `git checkout autoresearch/[skill-name]`
5. Re-validate the run harness before resuming. If the harness changed, log a new baseline or explicitly mark the run as a new phase.
6. Resume the experiment loop from where it left off — skip directly to step 5 or step 6 as appropriate
7. New experiment numbers continue from the last one (e.g., if last was exp-7, next is exp-8)

If a new model is being used, also read the research log:

```
Here is the research log for [SKILL_NAME].
It documents [N] meaningful revisions over [DAYS] days.
The last direction was [LATEST_DIRECTION].
Continue optimizing from this point.
Avoid repeating approaches that scored poorly (see discarded entries).
```

---

## limitations

| Limitation | Mitigation |
|---|---|
| Evals check structure, not true quality | Human review catches subjective issues early; false positive tracking corrects over time |
| Too-strict evals kill creativity | Keep evals to 3-6 core checks; everything else is a guideline |
| AI can "game" evals | Write evals at the principle level, not micro-rules; periodic human review |
| Cost (API calls add up) | Control via runs-per-experiment and budget cap |
| Overfitting to test inputs | Diverse test prompts; rotate prompts periodically |
| Eval criteria may be wrong | False positive tracking (step 10) corrects eval drift |
| Sequential runs may leak context | Note context contamination risk in log; use fresh runs when available |

---

## the test

A good autoresearch run:

1. **Started with a baseline** — never changed anything before measuring
2. **Used appropriate eval types** — binary for rules, comparative for quality, fidelity for pipelines; at least 50% Tier 1-2 evals
3. **Got human input early** — direction validated before going autonomous
4. **Mutated at the right level** — L1 for rules, L2 for assets, L3 for eval calibration
5. **Kept a complete log** — every experiment recorded with skill_lines
6. **Used git ratcheting** — each mutation committed, discards reset, clean linear history
7. **Maintained simplicity** — prompt didn't bloat; periodic deletion experiments ran
8. **Maintained a research log** — direction shifts captured for future models
9. **Improved the score** — measurable improvement from baseline to final
10. **Didn't overfit** — the skill got better at the actual job, not just at passing tests
11. **Quality improved, not just compliance** — before/after comparisons confirm real improvement

If the skill passes all evals but actual output quality hasn't improved — the evals are bad, not the skill. Go to step 10 and fix the evals.
