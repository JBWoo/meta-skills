# Design Principles for Codex Agent Workflows

## 1. Default Architecture

- 기본값은 `single Codex agent + skills/scripts` 조합이다.
- Claude Code의 `Task` 기반 서브에이전트 설계를 그대로 옮기지 않는다.
- 역할 분리가 필요해도 먼저 skill 분리로 해결하고, 문서 안에는 조정 비용과 이유를 적는다.

## 2. Folder Structure

```text
/project-root
  AGENTS.md
  /.codex
    /skills/<skill-name>/
      SKILL.md
      /agents/openai.yaml
      /scripts/       # optional
      /references/    # optional
      /assets/        # optional
  /output/
  /scripts/           # optional
  /docs/              # optional
```

원칙:

- 최종 문서는 프로젝트 루트의 `./blueprint-<task-name>.md`
- 중간 산출물은 `output/` 아래에 저장
- Claude 전용 경로인 `.claude/commands`, `.claude/agents`, `AGENT.md`는 Codex 설계에 넣지 않는다

## 3. LLM vs Deterministic Work

| LLM이 맡는 일 | 코드/스크립트가 맡는 일 |
|---|---|
| 분류, 우선순위 판단, 정성 평가, 요약, 누락 탐지 | 파일 I/O, 포맷 변환, 반복 처리, 외부 API 호출, 정적 검사, 스키마 검증 |

판단이 필요한 부분은 LLM에 남기고, 재현성과 실패 복구가 중요한 부분은 스크립트로 뺀다.

## 4. Validation Pattern

각 단계마다 최소 하나의 검증 방식을 정의한다.

| 유형 | 사용할 때 |
|---|---|
| Schema validation | JSON, CSV, 정형 산출물 |
| Rule-based validation | 개수, 섹션 유무, 경로 규칙 |
| LLM self-check | 요약 품질, 누락 여부, 톤 |
| Human review | 고위험 의사결정, 외부 전달 문서 |

## 5. Failure Handling

| 패턴 | 기준 |
|---|---|
| Auto retry | 누락, 형식 오류처럼 자동 복구 가능한 경우 |
| Needs user input | 판단 기준이 모호하거나 정책 선택이 필요한 경우 |
| Abort with log | 잘못된 입력, 권한 부족, 복구 불가 오류 |

실패 처리는 단계 설명 안에 구체적으로 적고, 재시도 횟수나 중단 기준을 명시한다.

## 6. Skill Design Rules

- skill 이름은 소문자 하이픈 형식 사용
- SKILL frontmatter 검증은 설치된 `skill-creator` 스킬의 `quick_validate.py`를 사용
- blueprint 문서 구조 검증은 설치된 `blueprint` 스킬의 `scripts/validate_blueprint_doc.py`를 사용
- skill 폴더에는 꼭 필요한 파일만 넣고 `README.md`, `CHANGELOG.md` 같은 부가 문서는 만들지 않는다

### Skill Creation Standards

블루프린트 설계서에 스킬이 포함될 경우, 구현 단계에서 반드시 **`skill-creator` 스킬**을 사용하여 스킬을 생성·검증해야 한다. 직접 SKILL.md를 손으로 작성하면 규격 불일치가 발생하므로 이를 방지하기 위한 필수 규칙이다.

#### 왜 skill-creator를 거쳐야 하는가

- **SKILL.md frontmatter 규격**: `name`, `description` 필수 필드 + 트리거 정확도를 위한 description 최적화가 필요
- **폴더 구조 규격**: `SKILL.md` + `scripts/`, `references/`, `assets/` 구조를 준수해야 함
- **Progressive disclosure**: SKILL.md 본문 500줄 이내, 대용량 참조는 `references/`로 분리
- **Description 최적화**: skill-creator의 description optimization 루프를 거쳐야 트리거 정확도가 보장됨
- **테스트 검증**: 테스트 프롬프트 실행 → 평가 → 개선 루프를 통해 스킬 품질 확보

#### 설계서에 포함할 내용

블루프린트 문서의 **구현 스펙 > Skill and Script Inventory** 또는 별도 섹션에 아래 내용을 명시:

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

## 7. Artifact Strategy

- 큰 중간 결과는 파일로 저장하고 경로만 다음 단계에 넘긴다
- 파일 이름 규칙은 `output/stepNN_<name>.<ext>`
- 최종 산출물은 루트에 두고, 중간 산출물과 분리한다

## 8. Documentation Scope

- 설계 문서에는 구조, 역할, 인터페이스, 검증 규칙만 쓴다
- 코드 본문, 장문 프롬프트, 세부 구현은 제외한다
- 구현 중 추정이 들어간 내용은 `Assumptions`나 해당 섹션 본문에서 명확히 표시한다
