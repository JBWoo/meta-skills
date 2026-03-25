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
10. **Execution mode** — Default: sequential in the current agent. Use subagents or delegated runs only if the user explicitly asks for delegation, parallel agent work, or subagents.

If the user provides an `evals.json` file, use that instead of asking for items 3-4.

**Execution mode rules:**
- Use `sequential` by default.
- Do not spawn subagents just because they might be faster; Codex requires explicit user permission for delegation.
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

### eval 유형 계층 (결정론성 높은 순)

eval을 작성할 때 가능한 한 상위 계층을 먼저 사용하라. LLM 판정은 마지막 수단이다.

**Tier 1 — 결정론적 체크 (최우선)**
grep, regex, 파일 존재 여부, JSON/YAML 파싱 성공, 글자 수 범위, 필수 섹션 존재 등.
동일 입력 → 항상 동일 결과. 가장 신뢰할 수 있다.

예시:
- "출력에 ## 요약 섹션이 있는가?" → `grep -q "^## 요약" output.md`
- "JSON으로 파싱 가능한가?" → `python -c "import json; json.load(open('output.json'))"`
- "500자 이상 2000자 이하인가?" → `wc -c output.txt | awk '{exit ($1<500 || $1>2000)}'`

**Tier 2 — 구조 검증**
출력의 구조적 특성을 프로그래밍적으로 검증. 약간의 파싱 로직이 필요하지만 여전히 결정론적.

예시:
- 마크다운 헤딩이 계층 순서를 지키는가? (H1 → H2 → H3)
- 테이블의 컬럼 수가 모든 행에서 일치하는가?
- 코드 블록에 언어 지정이 되어 있는가?

**Tier 3 — LLM-as-judge (최후 수단)**
내용의 질, 톤, 정확성 등 프로그래밍적 검증이 불가능한 항목에만 사용.

**목표: 전체 eval의 최소 50%를 Tier 1-2로 구성하라.** Tier 3만으로 구성된 eval suite는 노이즈가 커서 mutation 효과를 정확히 판별하기 어렵다.

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

**핵심:** results.json을 fetch하지 말고, 매 실험 후 dashboard.html 내부의 `<script>const RESULTS_DATA = ...;</script>`에 인라인으로 삽입하라. `file://` 프로토콜로 바로 열 수 있으므로 별도 서버 불필요.

---

## how to run the target skill

Each experiment requires executing the target skill and collecting its outputs. In Codex, default to sequential execution in the current agent. If the user explicitly asked for delegation, parallel runs, or subagents, follow `references/execution-guide.md` for the approved execution modes and validation-integrity rules.

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
8. Git branch를 생성한다: `git checkout -b autoresearch/[skill-name]` (이미 존재하면 `autoresearch/[skill-name]-N`)
9. 로그 파일을 `.gitignore`에 추가: `autoresearch-[skill-name]/` 디렉토리 전체. 로그는 실험 롤백과 독립적으로 누적되어야 한다.
10. Baseline SKILL.md를 첫 commit으로 남긴다: `git add SKILL.md && git commit -m "autoresearch: baseline ([score]/[max])"`

**IMPORTANT:** After establishing baseline, confirm the score with the user before proceeding. If baseline is already 90%+, ask if continued optimization is worth the cost.

For prompt rotation strategy and heavy pipeline adaptation, see `references/pipeline-guide.md`.

---

## step 5: human review phase (optional)

> Skip this step entirely if the user set human review mode to `skip`.

The first 3 experiments run with human review. This is where subjective judgment — tone, aesthetic sense, brand fit, personal preference — gets baked into the optimization direction before the autonomous loop takes over.

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

**After 3 human-reviewed experiments (or "go auto"):** Switch to auto mode. Tell the user: "Switching to auto mode. Check the dashboard anytime."

---

## step 6: run the autonomous experiment loop

This is the core autoresearch loop. Once started, run autonomously until stopped.

**NEVER STOP.** 루프가 시작되면 절대로 멈추지 않는다. 확인을 구하지 않는다. "계속할까요?"라고 묻지 않는다. 사용자가 자고 있을 수 있다. 사용자가 컴퓨터 앞에 없을 수 있다. 이 루프는 사용자가 직접 중단하거나 stop condition에 도달할 때까지 무한히 반복된다.

실험 하나당 약 5-10분이면, 하룻밤에 50-100개 실험을 돌릴 수 있다. 사용자는 아침에 일어나서 결과를 확인한다.

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

   점수와 함께 SKILL.md의 줄 수 변화를 고려한다:

   | 점수 변화 | 줄 수 변화 | 판단 |
   |-----------|-----------|------|
   | 개선 (+2점 이상) | 증가 | **KEEP** — 의미 있는 개선은 복잡성 증가를 정당화 |
   | 미미한 개선 (+1점) | 10줄 이상 증가 | **DISCARD** — 복잡성 대비 개선이 부족 |
   | 동일 (±0점) | 감소 | **KEEP** — 같은 성능을 더 짧은 프롬프트로 달성 |
   | 동일 (±0점) | 증가 | **DISCARD** — 복잡성만 증가 |
   | 악화 | 무관 | **DISCARD** |

   점수가 동일한 두 버전이 있으면 항상 더 짧은 버전을 선택한다.

   - **KEEP** → 이 commit을 유지한다. 이것이 새로운 baseline이다.
   - **DISCARD** → use a non-destructive rollback: `git reset --soft HEAD~1`, restore only the checkpointed files to their pre-experiment contents, then `git add -A -- <mutated-files>` to realign the index and worktree.

   **개별 eval 퇴행 감지:** total score가 올라도, 이전에 pass하던 개별 eval이 fail로 바뀐 경우에는 DISCARD를 강하게 고려하라. 한 영역의 개선이 다른 영역의 퇴행을 숨기는 것은 장기적으로 스킬 품질을 해친다.

8. **Log the result** and update results.json / dashboard.

9. **If this was a direction-level change**, log it in research-log.json (see step 7).

10. **Repeat.** Go back to step 1.

### Mutation safety rules (with git ratcheting)

- Each mutation is committed before the experiment runs: `git add <mutated-files> && git commit -m "autoresearch: [description]"`.
- KEEP → the commit stays. This is the new baseline.
- DISCARD → `git reset --soft HEAD~1`, then restore only the checkpointed files to their pre-experiment state. If a file was clean before the experiment, `git restore --source=HEAD --staged --worktree -- <path>` is acceptable after the soft reset. If it already had local changes, restore from the checkpoint copy instead of `HEAD`.
- Never use broad repo resets, `git reset --hard`, or commands that revert unrelated user changes.
- If the target repo is already dirty, record which files were pre-modified before the run and exclude them from discard logic unless this experiment changed them.
- The result is a clean linear git history where every surviving commit is a score improvement.

### 주기적 삭제 실험

매 5번째 실험마다 의도적으로 "삭제 mutation"을 시도하라. 최근 추가된 규칙 중 점수에 실제로 기여하지 않는 것을 찾아 제거한다. 규칙을 빼서 점수가 유지되면 그것은 최고의 실험 결과다. SKILL.md가 baseline 대비 200% 이상 비대해지면 changelog에 경고를 기록한다.

### stop conditions

- The user manually stops you
- Budget cap reached
- 95%+ pass rate for 3 consecutive experiments (or custom termination conditions — see `references/mutation-guide.md`)
- System-level timeout or resource limit

아이디어가 떨어졌다는 것은 멈출 이유가 아니다 → 아래 "when stuck" 전략을 참조하라.

### when stuck — 스킬 프롬프트 최적화 전용 전략

3회 연속 discard거나 아이디어가 떨어졌을 때:

1. **순서 재배치**: 가장 자주 실패하는 eval과 관련된 instruction을 SKILL.md 상단으로 이동. LLM은 프롬프트 초반의 지시를 더 강하게 따르는 경향이 있다.
2. **부정형 → 긍정형 전환**: "~하지 마라" → "반드시 ~하라" 형태로. 예: "목록에 번호를 붙이지 마라" → "모든 목록은 불릿(•)으로 시작하라"
3. **예시 교체**: 새 예시를 추가하는 대신, 기존 예시를 실패 패턴을 직접 해결하는 예시로 교체. 예시 수는 늘리지 않는다.
4. **제거 실험**: instruction을 하나 제거하고 점수를 측정. 서로 충돌하는 instruction이 있으면 제거가 곧 개선이다.
5. **구체성 증가**: 모호한 instruction에 구체적 수치/포맷 추가. 예: "간결하게 써라" → "각 섹션은 3-5문장으로 제한하라"
6. **역할(persona) 조정**: 스킬 도입부의 역할 설명을 변경. 예: "당신은 전문 기술 문서 작성자입니다" → "당신은 비개발자를 위한 기술 가이드 작성 전문가입니다"
7. **이전 near-miss 조합**: changelog에서 각각 discard됐지만 점수가 baseline과 비슷했던 mutation 2개를 동시에 적용. (이 경우에 한해 "한 번에 한 가지" 규칙의 예외를 허용)

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
8. **프롬프트 크기 변화:** baseline SKILL.md 줄 수 → 최종 SKILL.md 줄 수
9. **The improved SKILL.md** (already saved in place)
10. **File locations** for all output files
11. **Git log:** `git log --oneline autoresearch/[skill-name]`으로 성공한 mutation들의 히스토리

---

## step 9: next steps

autoresearch는 일회성이 아니라 지속적 개선 시스템이다.

**1주 후: 실전 검증**
실제 사용에서 개선된 스킬의 출력 품질을 확인한다. eval 점수가 높지만 실제 출력이 기대에 못 미치면 eval 기준이 잘못된 것이다.
→ eval을 수정하고 새로운 baseline부터 다시 시작하라.

**모델 업그레이드 시: 이어서 최적화**
새 모델이 나오면 changelog.md와 results.tsv를 참조하여 이전 모델이 도달한 지점부터 이어서 최적화한다:

```
이 스킬의 autoresearch 기록이 있습니다.
changelog.md에 [N]번의 실험이 기록되어 있고,
최종 pass rate는 [X]%입니다.
이 지점부터 계속 최적화해주세요.
```

**스킬 구조 변경 시: Baseline 재측정**
SKILL.md의 구조를 크게 바꿨거나 references/ 파일을 추가/삭제했다면, 기존 autoresearch 폴더를 아카이브하고 새로운 baseline부터 시작한다. 이전 changelog는 "어떤 방향이 효과가 있었는지"의 참고 자료로 활용한다.

**정기 리뷰 (월 1회 권장)**
changelog.md의 패턴을 리뷰한다:
- 같은 유형의 mutation이 반복 discard되면 → 접근법 자체를 변경
- 삭제 실험이 계속 KEEP되면 → 스킬이 비대해진 신호
- 최근 5회 실험이 모두 ±0점이면 → eval 기준을 재검토할 시점

---

## step 10: false positive tracking (outer loop)

Eval score가 높은데 실제 출력 품질이 낮으면 false positive. 10+ real-world output이 쌓인 후 월간 리뷰로 실행. See `references/eval-guide.md` (false positive tracking section) for the full process.

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
└── runs/                   # one folder per experiment
    ├── baseline/
    ├── exp-1/
    └── exp-N/
```

Plus the improved SKILL.md saved back to its original location.
Git branch `autoresearch/[skill-name]`에 성공한 mutation들의 선형 히스토리가 남는다.

---

## worked example

5회 실험의 전체 흐름 (git ratcheting, skill_lines, simplicity 판단, 삭제 실험, Tier 1/2/3 혼합 eval)을 보여주는 구체적 예시는 `references/worked-example.md`를 참조하라.

---

## resuming a previous run

If `autoresearch-[skill-name]/` already exists, do NOT create a new folder or re-establish baseline. Continue from the previous run:

1. Read `changelog.md` and `research-log.json` to understand what was already tried
2. Load `results.json` to find the current best score and next experiment number
3. Read `SKILL.md.baseline` to understand the original starting point
4. If autoresearch branch exists, `git checkout autoresearch/[skill-name]`
5. Resume the experiment loop from where it left off — skip directly to step 5 or step 6 as appropriate
6. New experiment numbers continue from the last one (e.g., if last was exp-7, next is exp-8)

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
