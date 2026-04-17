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

**경계 사례 판단 기준:**

| 작업 | 판단 | 이유 |
|------|------|------|
| 데이터 정제 (규칙 기반 필터) | 스크립트 | 조건이 명확하면 재현성이 중요 |
| 데이터 정제 (맥락 의존 판단) | 에이전트 | "이 데이터가 유효한가?"는 판단이 필요 |
| 에러 메시지 분류 | 에이전트 | 패턴이 다양하고 새로운 유형이 등장 |
| 포맷 변환 + 예외 처리 | 스크립트 + 에이전트 폴백 | 정상 케이스는 스크립트, 파싱 실패 시 에이전트가 판단 |

> 원칙: **재현성과 실패 복구가 중요하면 스크립트**, **판단이 필요하거나 패턴이 다양하면 에이전트**

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

에이전트가 Phase 2에서 아래 기준으로 자체 결정한다. 사용자에게 묻지 않는다.

**Single agent** (default):
- 워크플로우가 순차적이고 전체 지시가 컨텍스트 윈도우의 30% 이내
- 단계 간 맥락 공유가 중요한 경우

**Sub-agent separation** (when needed):
- 전체 지시가 컨텍스트 윈도우의 30%를 초과 — 항상 로드하기엔 너무 길다
- 명확히 독립적인 작업 블록이 있고, 각각 다른 도메인 지식이 필요
- 병렬 실행이 가능하고 그로 인한 속도 이점이 명확한 경우

> 판단이 애매하면 단일 에이전트를 선택한다. 멀티 에이전트의 조정 비용(데이터 전달, 오류 전파, 디버깅 복잡도)은 과소평가되기 쉽다.

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

| | Skill | Sub-agent |
|---|-------|-----------|
| **단위** | 단일 작업/도구 (입력 → 출력이 명확) | 여러 단계를 자율적으로 수행하는 역할 |
| **판단** | 자체 판단 불필요 또는 최소 | 자체 판단이 핵심 (분류, 평가, 전략 선택) |
| **재사용** | 여러 에이전트에서 공유 가능 | 특정 워크플로우 전용 |
| **상태** | 무상태 (호출 시마다 독립) | 유상태 (여러 단계의 맥락 유지) |
| **예시** | `file-parser`, `api-caller`, `format-converter` | `code-reviewer`, `report-generator`, `curriculum-designer` |

> **판단 기준**: "이 컴포넌트가 독립적으로 여러 단계를 수행하고 자체 판단이 필요한가?" → Yes면 sub-agent, No면 skill.

## Blueprint 복잡도 한계

이 스킬로 설계하는 시스템의 권장 한계:

| 항목 | 권장 한계 | 초과 시 |
|------|----------|---------|
| 워크플로우 단계 수 | 10개 이내 | 하위 워크플로우로 분할 검토 |
| 서브에이전트 수 | 4개 이내 | 조정 복잡도 급증 — 계층 분리 검토 |
| 스킬 수 | 8개 이내 | 스킬 간 중복/의존성 점검 |

한계를 초과하면 설계서에 경고를 명시하고, 분할 방안을 함께 제시한다.

## CLAUDE.md / AGENTS.md 작성 원칙

블루프린트로 설계된 시스템의 CLAUDE.md와 AGENTS.md는 아래 4가지 원칙을 따라 작성해야 한다. 규칙을 나열하지 말고, 원칙을 깊이 이해시켜라.

### 원칙 1: 구현 전에 생각하라 (Think Before Coding)

가정을 숨기지 말고, 트레이드오프를 드러내라.

- 에이전트가 구현 전에 가정을 명시적으로 진술하도록 지시
- 해석이 여러 개일 때 조용히 하나를 고르지 말고 선택지를 제시하도록 유도
- 더 단순한 접근이 있으면 말하도록 허용 — 필요 시 pushback 권한 부여
- 불명확한 부분은 멈추고 물어보도록 명시

### 원칙 2: 단순함 우선 (Simplicity First)

문제를 해결하는 최소한의 코드. 추측성 구현 금지.

- 요청한 것 이상의 기능 금지
- 일회성 코드에 추상화 금지
- 요청하지 않은 "유연성"이나 "설정 가능성" 금지
- 불가능한 시나리오에 대한 에러 핸들링 금지

**자기 검증 테스트**: "시니어 엔지니어가 보고 '이거 너무 복잡하다'고 할까?" → 그렇다면 단순화.

### 원칙 3: 수술적 변경 (Surgical Changes)

건드려야 할 것만 건드려라. 자기가 만든 잔해만 정리하라.

- 인접 코드, 주석, 포매팅을 "개선"하지 말 것
- 깨지지 않은 것을 리팩터링하지 말 것
- 기존 스타일과 다르더라도 기존 스타일에 맞출 것
- 관련 없는 데드 코드는 언급만 하고 삭제하지 말 것

**자기 검증 테스트**: "변경된 모든 줄이 사용자의 요청에 직접 연결되는가?" → 아니면 되돌려라.

### 원칙 4: 목표 중심 실행 (Goal-Driven Execution)

성공 기준을 정의하고, 검증될 때까지 반복하라.

작업을 검증 가능한 목표로 변환:
- "유효성 검사 추가" → "잘못된 입력에 대한 테스트를 쓰고, 통과시켜라"
- "버그 수정" → "재현하는 테스트를 쓰고, 통과시켜라"

멀티스텝 작업은 간략한 계획을 명시:
```
1. [단계] → 검증: [확인 방법]
2. [단계] → 검증: [확인 방법]
```

### 적용 방법

CLAUDE.md에 이 4가지 원칙을 직접 넣되, **50줄 이내의 간결한 형태**로 압축한다. 규칙 50개보다 원칙 4개가 LLM의 실제 준수율이 높다.

각 원칙에는 반드시 **자기 검증 질문**을 포함한다 — 추상적 지시 대신 에이전트가 스스로 판단할 수 있는 구체적 기준을 제공한다.

**트레이드오프 명시**: 원칙의 적용 범위와 한계를 명시한다. 예: "이 가이드라인은 신중함 쪽에 편향되어 있다. 단순 작업에는 판단력을 사용하라." 절대적 규칙은 역효과를 낸다.

**성공 지표**: CLAUDE.md 끝에 "이 가이드라인이 잘 작동하고 있다면:" 항목을 추가한다. 예:
- diff에 불필요한 변경이 줄어든다
- 과도한 복잡성으로 인한 재작성이 줄어든다
- 구현 전에 명확화 질문이 먼저 나온다

---

## Skill Creation Standards

블루프린트로 설계된 모든 시스템에서 구현 단계에서 반드시 **`skill-creator` 스킬**을 사용하여 스킬을 생성·검증해야 한다. 설계서에 스킬이 포함되어 있는지 여부와 무관하게, 스킬을 구현할 때 직접 SKILL.md를 손으로 작성하는 것은 금지된다. 규격 불일치 및 트리거 실패를 방지하기 위한 필수 규칙이다.

### 왜 skill-creator를 거쳐야 하는가

- **SKILL.md frontmatter 규격**: `name`, `description` 필수 필드 + 트리거 정확도를 위한 description 최적화가 필요
- **폴더 구조 규격**: `SKILL.md` + `scripts/`, `references/`, `assets/` 구조를 준수해야 함
- **Progressive disclosure**: SKILL.md 본문 500줄 이내, 대용량 참조는 `references/`로 분리
- **Description 최적화**: skill-creator의 description optimization 루프를 거쳐야 트리거 정확도가 보장됨
- **테스트 검증**: 테스트 프롬프트 실행 → 평가 → 개선 루프를 통해 스킬 품질 확보

### 설계서에 포함할 내용

블루프린트 문서의 **구현 스펙 > 스킬/스크립트 목록** 또는 별도 섹션에 아래 내용을 명시:

```markdown
## 스킬 생성 규칙

이 설계서에 정의된 모든 스킬은 구현 시 반드시 `skill-creator` 스킬(`/skill-creator`)을 사용하여 생성할 것.
직접 SKILL.md를 수동 작성하지 말 것 — 규격 불일치 및 트리거 실패의 원인이 됨.

skill-creator가 보장하는 규격:
1. SKILL.md frontmatter (name, description) 필수 필드 준수
2. description의 트리거 정확도 최적화 (eval 기반 optimization loop)
3. 폴더 구조 (SKILL.md + scripts/ + references/) 규격 준수
4. 테스트 프롬프트 실행 및 품질 검증 완료
```
