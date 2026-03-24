---
name: autoresearch
description: Autonomously optimize any Claude Code skill by running it repeatedly, scoring outputs against evals (binary for rules + comparative for quality), mutating the skill's prompt and reference assets, and keeping improvements. Based on Karpathy's autoresearch methodology. Use this skill whenever the user mentions optimizing a skill, improving a skill, running autoresearch, making a skill better, self-improving a skill, benchmarking a skill, evaluating a skill, running evals on a skill, or any request to iteratively test and refine a skill — even if they don't use the word "autoresearch" explicitly. Also trigger on 스킬 개선, 스킬 최적화, 스킬 벤치마크, 스킬 평가. Outputs an improved SKILL.md, a results log, a changelog, and a research log of meaningful direction shifts.
---

# Autoresearch for Skills

Most skills work about 70% of the time. The other 30% you get garbage. The fix isn't to rewrite the skill from scratch. It's to let an agent run it dozens of times, score every output, and tighten the prompt until that 30% disappears.

This skill adapts Andrej Karpathy's autoresearch methodology (autonomous experimentation loops) to Claude Code skills. Instead of optimizing ML training code, we optimize skill prompts.

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

**STOP. Do not run any experiments until all fields below are confirmed with the user.**

1. **Target skill(s)** — Which skill to optimize? (exact path to SKILL.md). For pipelines, list all skills in execution order.
2. **Pipeline mode** — Single skill or multi-skill pipeline? Default: single. See `references/pipeline-guide.md` for pipeline details.
3. **Test inputs** — 3-5 different prompts/scenarios. Variety matters — cover different use cases to avoid overfitting.
4. **Eval criteria** — Binary checks for rules (3-6) + comparative checks for quality dimensions (0-5). See `references/eval-guide.md`.
5. **Runs per experiment** — How many times to run the skill per mutation? Default: 5.
6. **Run interval** — How often experiments cycle. Default: every 2 minutes.
7. **Budget cap** — Optional. Max experiment cycles before stopping. Default: no cap.
8. **Termination conditions** — When to stop auto mode. Default: 95%+ for 3 consecutive. See `references/mutation-guide.md` for custom conditions.
9. **Human review mode** — Review the first few experiments before full auto? Default: yes (first 3). Set to `skip` for fully autonomous.

If the user provides an `evals.json` file, use that instead of asking for items 3-4.

---

## step 1: read the skill

Before changing anything, read and understand the target skill completely.

1. Read the full SKILL.md file
2. Read any files in `references/` that the skill links to
3. Identify the skill's core job, process steps, and output format
4. Note any existing quality checks or anti-patterns already in the skill

Do NOT skip this. You need to understand what the skill does before you can improve it.

For **pipeline mode**, read `references/pipeline-guide.md` and map the full data flow across all skills.

---

## step 2: build the eval suite

Convert the user's eval criteria into a structured test using two or three eval types.

### Binary evals — objective rule compliance

Use these for hard rules that have a clear yes/no answer.

```
EVAL [number]: [Short name]
Type: binary
Question: [Yes/no question about the output]
Pass condition: [What "yes" looks like — be specific]
Fail condition: [What triggers a "no"]
```

### Comparative evals — subjective quality improvement

Binary evals plateau once the skill follows the rules — they can't tell you if one output is *better* than another. Comparative evals judge whether a mutation actually improved quality along a specific dimension.

```
EVAL [number]: [Short name]
Type: comparative
Dimension: [One specific quality aspect to compare]
Method: Generate baseline output and mutated output from the same prompt.
        Compare side-by-side (screenshots for visual, text diff for prose/code).
        Agent picks the winner on this dimension.
Pass condition: Mutated version wins or ties.
Fail condition: Baseline version is clearly better.
```

Any skill with subjective quality can benefit from comparative evals:

| Skill type | Example comparative dimensions |
|-----------|-------------------------------|
| Visual/design | Layout composition, color usage, whitespace balance, visual variety |
| Writing | Tone consistency, opening hook strength, paragraph flow |
| Code generation | Readability, idiomatic patterns, naming quality |
| Documentation | Information architecture, example quality, scannability |

### Fidelity evals — pipeline stage consistency (pipeline mode only)

For multi-skill pipelines, fidelity evals measure how accurately the downstream output preserves the upstream output's quality. See `references/pipeline-guide.md` for the full template and common fidelity dimensions.

### Comparative eval rules

- Each eval tests ONE dimension — don't bundle "is it better overall?"
- The agent must see both outputs simultaneously — never judge one in isolation
- A tie is a pass (mutation didn't hurt this dimension)
- 3-5 comparative evals alongside the binary evals

**Agent-as-Judge for comparative evals:**

For visual outputs (slides, UI, designs):
1. Capture screenshots of baseline and mutated outputs
2. Read both screenshots using the Read tool (multimodal) in a single evaluation step
3. Judge each dimension one at a time: state the dimension, describe what you see in each, verdict (A wins / B wins / TIE)
4. Randomize which output is labeled A/B across experiments to avoid position bias

For text/code outputs: read both inline, compare on the stated dimension, same verdict format.

**Judging discipline:**
- Judge each dimension independently — don't let one strong dimension bias others
- If you genuinely can't decide, it's a TIE (counts as pass)
- Log the verdict and reasoning in changelog.md

**Scoring:** Binary: pass=1, fail=0. Comparative: win=1, tie=0.5, loss=0. Fidelity: pass=1, fail=0. Total = sum of all.

### Rules for all evals

- Specific enough to be consistent. "Is the text readable?" is too vague. "Are all words spelled correctly with no truncated sentences?" is testable.
- Not so narrow that the skill games the eval.
- **Every skill should have at least 1-2 comparative evals alongside binary checks.** Binary evals alone plateau quickly — the most common autoresearch failure mode.
- Each eval should test something distinct — no overlapping checks.

**Before finalizing, run the 3-question test on each eval:**

1. Could two different agents score the same output and agree? (if not -> tighten)
2. Could a skill game this eval without actually improving? (if yes -> too narrow)
3. Does this eval test something the user actually cares about? (if not -> drop it)

See `references/eval-guide.md` for detailed examples, the assertion category taxonomy, and how to convert subjective criteria into testable checks.

**Scoring unit:** Each test prompt has multiple assertions. `max_score = total assertions x runs per experiment`.

---

## step 3: generate the live dashboard

The dashboard is the user's window into the optimization. Without it, auto mode is a black box.

Before running any experiments, create a live HTML dashboard at `autoresearch-[skill-name]/dashboard.html` and open it.

The dashboard must:

- Auto-refresh every 10 seconds (reads from results.json)
- Show a score progression line chart (experiment on X, pass rate % on Y)
- Show colored bars per experiment: green=keep, red=discard, blue=baseline, yellow=human-reviewed
- Show a table of all experiments with: #, score, pass rate, status, description
- Show per-eval breakdown: which evals pass most/least
- Show current status: "Running experiment [N]..." or "Awaiting human review" or "Idle"

**If comparative evals are used — add a comparison view** with before/after output pairs and per-dimension verdicts.

Generate as a single self-contained HTML file with inline CSS/JS. Use Chart.js from CDN.

**Serving:** Start a local HTTP server (don't use `file://` — CORS blocks fetch):

```bash
python -m http.server 8787 --directory autoresearch-[skill-name] &
```

Open `http://localhost:8787/dashboard.html` immediately. Kill the server when the run is complete.

**Update `results.json`** after every experiment with: skill_name, status, mode, current_experiment, experiments array (id, score, pass_rate, status, description, comparative verdicts), eval_breakdown, and termination_check. When the run finishes, set status to `"complete"`.

---

## step 4: establish baseline

Run the skill AS-IS before changing anything. This is experiment #0.

1. Create working directory: `autoresearch-[skill-name]/`
2. Create `results.json`, `changelog.md`, `research-log.json`, and `dashboard.html`, then open the dashboard
3. Back up the original SKILL.md as `SKILL.md.baseline`
4. Run the skill using the test inputs
5. Score every output against every eval
6. Record the baseline score and update results.json

**IMPORTANT:** After establishing baseline, confirm the score with the user before proceeding. If baseline is already 90%+, ask if continued optimization is worth the cost.

For prompt rotation strategy and heavy pipeline adaptation, see `references/pipeline-guide.md`.

---

## step 5: human review phase (optional)

> Skip this step entirely if the user set human review mode to `skip`.

The first 3 experiments run with human review. This is where subjective judgment — tone, aesthetic sense, brand fit, personal preference — gets baked into the optimization direction before the autonomous loop takes over.

**Why 3 experiments:**
- Experiment 1: The biggest, most obvious fix. Human confirms the direction.
- Experiment 2: Second-priority fix. Human catches taste/tone drift.
- Experiment 3: Direction established. Human gives final go/no-go for auto mode.

**For each human-reviewed experiment:**

1. **Analyze failures** and form a hypothesis (same as step 6)
2. **Make ONE change** to SKILL.md
3. **Run the experiment** and score it
4. **Present results** showing: the change and why, before/after score, 2-3 sample outputs, keep/discard recommendation
5. **Ask the user:** "Does this direction feel right?" / "Anything the evals aren't catching?"
6. **If subjective feedback is given**, note it in changelog.md as `[HUMAN INSIGHT]` and incorporate into SKILL.md. Do NOT add it as a new eval.
7. **Log the result** with status `human-reviewed`.

**After 3 human-reviewed experiments (or "go auto"):** Switch to auto mode. Tell the user: "Switching to auto mode. Check the dashboard anytime."

---

## step 6: run the autonomous experiment loop

This is the core autoresearch loop. Once started, run autonomously until stopped.

**Do not stop between experiments.** Don't pause for confirmation, don't ask "should I continue?". The user chose auto mode because they want you to keep going.

**LOOP:**

1. **Analyze failures.** Look at which evals fail most. Read the actual failing outputs. Identify the pattern.

2. **Form a hypothesis.** Pick a mutation at the right level. See `references/mutation-guide.md` for the three mutation levels (L1: prompt rules, L2: reference assets, L3: eval calibration), good/bad mutation examples, bundled mutations, and L1->L2 transition signals.

3. **Make the change.** Edit the target file(s) at the chosen mutation level.

4. **Run the experiment.** Execute the skill with the test inputs. Save outputs.

5. **Score it.** Run every output through every eval. Calculate total score.

6. **Decide: keep or discard.**
   - Score improved -> **KEEP.** This is the new baseline.
   - Score unchanged -> **DISCARD.** Revert to previous version.
   - Score worse -> **DISCARD.** Revert to previous version.

7. **Log the result** and update results.json / dashboard.

8. **If this was a direction-level change**, log it in research-log.json (see step 7).

9. **Repeat.** Go back to step 1.

**Stop conditions:**
- The user manually stops you
- Budget cap reached
- 95%+ pass rate for 3 consecutive experiments (or custom termination conditions — see `references/mutation-guide.md`)
- System-level timeout or resource limit

**If you run out of ideas:** Re-read failing outputs. Combine previous near-miss mutations. Try a completely different approach. Try removing things instead of adding. Simplification that maintains the score is a win.

---

## step 7: maintain the logs

Three files, three different jobs. Keep them separate.

### changelog.md — every experiment, kept or discarded

```markdown
## Experiment [N] — [keep/discard/human-reviewed]

**Score:** [X]/[max] ([percent]%)
**Change:** [One sentence describing what was changed]
**Reasoning:** [Why this change was expected to help]
**Result:** [What actually happened — which evals improved/declined]
**Failing outputs:** [Brief description of what still fails]
**Human insight:** [If any subjective feedback was given]
```

### research-log.json — direction shifts only

NOT every experiment goes here. Only log **direction shifts** — meaningful changes in approach, strategy, or framing.

```json
{
  "skill_name": "[name]",
  "entries": [
    {
      "revision_number": 3,
      "date": "2026-03-25",
      "change_summary": "Switched from announcement tone to curiosity-trigger tone",
      "change_rationale": "Announcement tone passed evals but felt generic in human review",
      "score_before": 32,
      "score_after": 35,
      "direction_shift": "announcement -> curiosity trigger",
      "source": "human-review | auto-loop | false-positive-correction",
      "model_used": "[model identifier]"
    }
  ]
}
```

The research log survives model upgrades. When a new model comes out, hand it the research log and it picks up where the previous model left off.

**Maintenance:** If exceeds 30 entries, keep the 10 most recent in full detail + a pattern summary of the rest.

### results.tsv — raw score data

Tab-separated, one row per experiment. Updated automatically. Powers the dashboard.

---

## step 8: deliver results

When the user returns or the loop stops, present:

1. **Score summary:** Baseline -> Final (percent improvement)
2. **Total experiments:** How many mutations tried
3. **Keep rate:** Kept vs discarded
4. **Top 3 changes that helped most** (from changelog)
5. **Human insights incorporated** (from the review phase, if any)
6. **Remaining failure patterns** (what still fails, if anything)
7. **Direction shifts** (from research-log.json)
8. **The improved SKILL.md** (already saved in place)
9. **File locations** for all output files

---

## step 9: false positive tracking (outer loop — periodic)

> Run this only when real-world performance data is available.

The inner loop optimizes the skill against eval criteria. But what if the eval criteria themselves are wrong? A high eval score with poor real-world results = **false positive**.

| Eval Score | Real Performance | Meaning | Action |
|---|---|---|---|
| High | High | Evals are working | Keep evals |
| High | Low | **False positive** | Fix evals |
| Low | High | Missing success pattern | Add new eval criteria |
| Low | Low | Correctly filtered | Keep evals |

**When to run:** After 10+ real-world outputs with performance data. Monthly review, not after every experiment.

**How to run:**
1. Compare eval winners against real performance
2. Identify false positives: high eval score but low real performance
3. Analyze what the evals missed
4. Update eval criteria and log with `"source": "false-positive-correction"`
5. Re-run the inner loop with updated evals

**Caution:** Need minimum 10 data points. Account for external factors (SEO changes, seasonality). Blog content has 1-2 week lag; social media is faster (24-48h).

---

## output format

```
autoresearch-[skill-name]/
├── dashboard.html          # live browser dashboard (auto-refreshes)
├── results.json            # data file powering the dashboard
├── changelog.md            # detailed log of every mutation
├── research-log.json       # direction shifts and strategic patterns only
├── SKILL.md.baseline       # original skill before optimization
└── runs/                   # one folder per experiment
    ├── baseline/
    ├── exp-1/
    └── exp-N/
```

Plus the improved SKILL.md saved back to its original location.

---

## resuming a previous run

If `autoresearch-[skill-name]/` already exists:

1. Read `changelog.md` and `research-log.json`
2. Load `results.json` to find the current score and next experiment number
3. Resume the loop from where it left off — don't re-establish baseline

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
| Eval criteria may be wrong | False positive tracking (step 9) corrects eval drift |

---

## the test

A good autoresearch run:

1. **Started with a baseline** — never changed anything before measuring
2. **Used appropriate eval types** — binary for rules, comparative for quality, fidelity for pipelines
3. **Got human input early** — direction validated before going autonomous
4. **Mutated at the right level** — L1 for rules, L2 for assets, L3 for eval calibration
5. **Kept a complete log** — every experiment recorded
6. **Maintained a research log** — direction shifts captured for future models
7. **Improved the score** — measurable improvement from baseline to final
8. **Didn't overfit** — the skill got better at the actual job, not just at passing tests
9. **Quality improved, not just compliance** — before/after comparisons confirm real improvement

If the skill passes all evals but actual output quality hasn't improved — the evals are bad, not the skill. Go to step 9 and fix the evals.
