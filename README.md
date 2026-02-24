# Jangpm Agent Workflow — Claude Code Skills

Claude Code에서 에이전틱 워크플로우를 설계하고 실행하는 데 사용하는 스킬 모음입니다.

## 포함된 스킬

| 스킬 | 트리거 | 설명 |
|------|--------|------|
| **blueprint** | `/blueprint` | 자동화할 작업을 인터뷰로 파악한 뒤, Claude Code 구현에 바로 쓸 수 있는 에이전트 시스템 설계서(`.md`)를 생성 |
| **deep-dive** | `/deep-dive` | 요구사항을 심층 인터뷰로 탐색한 뒤, 스펙 문서를 작성하거나 기존 문서를 업데이트 |
| **reflect** | `/reflect` | 세션 종료 시 4개 에이전트를 병렬 실행해 문서 업데이트·자동화 아이디어·학습 내용·다음 액션을 정리 |

---

## 설치 방법

### 방법 1 — 프로젝트 전용 (이 레포를 클론해서 사용)

이 레포를 클론하면 `.claude/skills/`와 `.claude/commands/`가 이미 있습니다.
해당 디렉토리에서 Claude Code를 실행하면 스킬과 커맨드가 자동으로 인식됩니다.

```bash
git clone <repo-url>
cd "Jangpm Agent Workflow"
claude
```

### 방법 2 — 전역 설치 (모든 프로젝트에서 사용)

skills와 commands 폴더를 각각 `~/.claude/`로 복사합니다.

**macOS / Linux:**
```bash
cp -r .claude/skills/blueprint  ~/.claude/skills/
cp -r .claude/skills/deep-dive  ~/.claude/skills/
cp -r .claude/skills/reflect    ~/.claude/skills/

cp .claude/commands/blueprint.md  ~/.claude/commands/
cp .claude/commands/deep-dive.md  ~/.claude/commands/
cp .claude/commands/reflect.md    ~/.claude/commands/
```

**Windows (PowerShell):**
```powershell
Copy-Item -Recurse .\.claude\skills\blueprint  "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse .\.claude\skills\deep-dive  "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse .\.claude\skills\reflect    "$env:USERPROFILE\.claude\skills\"

Copy-Item .\.claude\commands\blueprint.md  "$env:USERPROFILE\.claude\commands\"
Copy-Item .\.claude\commands\deep-dive.md  "$env:USERPROFILE\.claude\commands\"
Copy-Item .\.claude\commands\reflect.md    "$env:USERPROFILE\.claude\commands\"
```

---

## 사용 방법

Claude Code 세션에서 슬래시 커맨드로 호출합니다.

```
/blueprint           # 에이전트 시스템 설계서 생성
/deep-dive           # 주제 심층 인터뷰 + 스펙 문서 작성
/reflect             # 세션 마무리 정리
```

인수를 넘길 수도 있습니다:

```
/deep-dive 사용자 알림 시스템
/blueprint 고객 리뷰 자동 분류 에이전트
```

---

## 스킬 구조

```
.claude/skills/
├── blueprint/
│   ├── SKILL.md                        # 워크플로우 지침
│   └── references/
│       ├── design-principles.md        # 에이전틱 시스템 설계 원칙
│       └── document-template.md        # 설계서 출력 템플릿
├── deep-dive/
│   └── SKILL.md
└── reflect/
    └── SKILL.md
```

---

## 라이선스

MIT
