# moneymate

뉴스로 인과 뼈대를 배우고(탭 1) → 큰손의 실제 매매를 그 뼈대로 읽고(탭 2) → 배운 뼈대가 나만의 인과 지도로 쌓이는(탭 3) 금융 학습 서비스입니다.

> 실행 방법은 개발이 진행되면서 채웁니다. (8주차 정리)

---

## 폴더 구조

| 폴더 | 역할 | 기술 |
| :--- | :--- | :--- |
| `web/` | 탭 3개 모바일 웹 화면 (390×844) | React, TypeScript, React Router, TanStack Query |
| `server/` | DB 읽기 중심 API, 답안 저장, 채점 요청 전달 | Node.js, Express, node-postgres(pg) |
| `worker/` | 수집·계산·출제·채점·검증, 하루 파이프라인 (계산하고 DB에 쓰는 쪽) | Python 3.12, pytest |
| `db/` | 스키마 마이그레이션(`migrations/`)과 초기 데이터(`seeds/`) | PostgreSQL (Docker Compose) |
| `docs/` | 서비스 흐름, 기술 확정안, 공통 규칙, 모듈 명세(`modules/`) | Markdown |
| `tradingagents/` | 탭 1 해설용 분석 리포트 (별도 venv, 6주차 시험) | TradingAgents |

`worker/` 하위 폴더

| 폴더 | 역할 |
| :--- | :--- |
| `collectors/` | 13F, ETF, 가격, 뉴스 수집 |
| `compute/` | 큰손 변화, 겹침, ETF 추세, 지표, 뉴스 선별 계산 |
| `concepts/` | 인과 뼈대 (경로 탐색, seeds 적재, 개념 제안) |
| `generate/` | LLM 호출, 출제, 이유 생성, 채점 (`prompts/`에 프롬프트) |
| `validate/` | 출제 결과 검증 (형식, 정답, 금지 표현, 중복, 근거 날짜) |
| `eval/` | 채점 신뢰도 (κ) |
| `tests/` | pytest (`fixtures/`에 샘플 데이터) |

- `worker`가 계산해서 DB에 쓰고, `server`는 DB에서 읽기만 합니다.
- 담당자는 개발 분담표 3장을 따릅니다. 공통 파일(스키마, `CLAUDE.md`, config, DB 연결)은 A만 수정하고, 나머지는 A에게 요청하거나 PR로 올립니다.
- API 키는 `.env`에만 둡니다. `.env.example`을 복사해서 씁니다.

---

## 협업 규칙

### 워크플로우

```
이슈 생성 → 브랜치 생성 → 작업 & 커밋 → PR 생성 → 리뷰 → develop 머지
```

1. GitHub에서 이슈를 생성합니다.
2. `develop`을 최신으로 받은 뒤 작업 브랜치를 만듭니다.
   ```bash
   git checkout develop
   git pull
   git checkout -b feat/etf-collector-12
   ```
3. 기능마다 커밋합니다.
4. `develop`을 대상으로 PR을 생성하고, 본문에 `close #이슈번호`를 적습니다.
5. 팀원 승인 1명 후 **Squash and merge** 합니다. 짝 리뷰 대상 모듈은 짝이 리뷰합니다.
6. 머지된 작업 브랜치는 삭제합니다.

> `main`과 `develop`에는 직접 push하지 않고, 반드시 PR로 머지합니다.

### 브랜치

```
type/설명-이슈번호
```

예시: `feat/etf-collector-12`, `fix/overlap-direction-34`

- 설명은 영어 소문자 + kebab-case로 쓰고, 끝에 이슈 번호를 붙입니다.

| 브랜치 | 역할 |
| :--- | :--- |
| `main` | 발표·배포되는 안정 버전. `develop`에서만 머지 |
| `develop` | 기능이 모이는 통합 브랜치. 평소 작업의 기준점 |
| 작업 브랜치 | 기능/수정 단위로 `develop`에서 분기 |

### 커밋

```
type: 메시지
```

예시: `feat: ETF 일일 스냅샷 수집기 추가`

- 타입은 소문자, 메시지는 한글로 무엇을 했는지 한 줄로 씁니다.
- 한 커밋에는 한 가지 의미 단위만 담습니다.
- PR 제목도 같은 형식으로 씁니다. (Squash and merge 시 PR 제목이 커밋 제목이 됩니다.)

| 타입 | 의미 |
| :--- | :--- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `style` | 코드 스타일 (의미 변화 X) |
| `design` | UI 디자인 변경 |
| `test` | 테스트 코드 |
| `refactor` | 리팩토링 (기능 변화 X) |
| `ci` | CI 설정 수정 |
| `perf` | 성능 개선 |
| `chore` | 자잘한 수정/설정 (의존성, 도구 설정) |
| `rename` | 파일/폴더명 변경 |
| `remove` | 파일 삭제 |

### PR

- 대상 브랜치는 `develop`입니다. (`main`으로의 PR은 배포 시에만)
- 관련 이슈는 `close #이슈번호`로 연결합니다.
- 리뷰는 **Approve**로 승인해야 인원으로 집계됩니다.
- 머지 방식은 **Squash and merge**입니다.

### 자동으로 검사되는 것

PR을 올리면 아래 검사가 돌고, 통과해야 머지할 수 있습니다.

| 항목 | 내용 |
| :--- | :--- |
| PR 제목 | `type: 메시지` 형식, 12종 타입만 허용 |
| 브랜치 이름 | `type/설명-이슈번호` 형식 (`develop` → `main` 배포 PR은 예외) |
| web lint·build | `web/`에서 `pnpm lint`, `pnpm build` (파일·변수 이름 규칙 포함) |
| `main`/`develop` 보호 | 직접 push 불가, PR + 승인 1명 필요 |

- 커밋은 Squash로 PR 제목 하나로 합쳐지므로, 작업 브랜치 안의 커밋 메시지는 따로 검사하지 않습니다. 그래도 규칙대로 쓰는 것을 권장합니다.
- worker의 pytest 검사는 코드가 생기면 추가합니다.

### 자주 하는 실수

- `develop`에서 바로 작업·커밋하기 → 반드시 작업 브랜치를 만들고 시작
- 이슈 없이 브랜치·PR 만들기 → 이슈를 먼저 만들고 브랜치 이름에 번호를 붙이기
- 리뷰를 **Comment**로만 남기기 → **Approve**를 눌러야 승인으로 집계됩니다
- 자기 PR을 자기가 승인하기 → 불가능, 다른 팀원이 승인해야 합니다
- PR 제목 타입을 대문자로 쓰거나 없는 타입 쓰기 (`Feat:`, `add:`)
- 다른 담당자의 공통 파일(스키마, `CLAUDE.md`, config, DB 연결) 직접 수정 → A에게 요청하거나 PR로
