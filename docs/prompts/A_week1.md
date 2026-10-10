# A의 1주차 — 클로드코드 프롬프트 모음

사용법: 터미널에서 `moneymate` 폴더로 이동 → `claude` 실행 → 아래 프롬프트를 **번호 순서대로 하나씩** 붙여넣는다.
한 프롬프트가 끝나면 결과를 눈으로 확인하고(명령어가 뭘 했는지 읽기) 다음으로 간다. 막히면 에러 메시지를 통째로 붙여넣고 "이 에러 원인과 해결을 알려줘"라고 한다.
각 프롬프트를 쓴 뒤 docs/AI_USAGE.md 에 한 줄 적는다 (보고서 재료).

---

## 프롬프트 0. 문서 읽히기 (5분)

```
CLAUDE.md 와 docs/ 안의 문서 4개(서비스흐름.md, 기술확정안.md, 개발분담표.md, conventions.md)를 읽어줘.
나는 이 프로젝트의 A 담당이고 지금은 1주차야. 읽은 뒤 아래 3가지를 10줄 이내로 정리해줘.
1) 1주차에 내가 끝내야 하는 것 2) B·C가 나를 기다리는 것 3) 문서끼리 안 맞거나 빠진 부분
코드는 아직 건드리지 마.
```

## 프롬프트 1. git 저장소와 첫 커밋 (10분)

```
이 폴더를 git 저장소로 만들고 첫 커밋을 해줘.
- .env 가 추적되지 않는지 git status 로 확인해서 보여줘
- 기본 브랜치 이름은 main
- 커밋 메시지: "init: 프로젝트 뼈대, 스키마 초안, 문서"
GitHub 원격 저장소 연결과 push 는 내가 직접 할 거니까, 어떤 명령을 치면 되는지만 알려줘.
```

> 직접 할 일: GitHub에서 빈 저장소 `moneymate` 생성(README 추가 체크 해제) → 안내받은 `git remote add origin ...` / `git push -u origin main` 실행 → Settings → Collaborators 에서 B·C 초대.

## 프롬프트 2. DB 띄우고 스키마 확인 (20분) ★ B·C가 기다림

```
.env.example 을 .env 로 복사하고, docker compose up -d 로 PostgreSQL 을 띄워줘.
그 다음 아래를 확인해서 결과를 보여줘.
1) docker compose ps 에서 db 가 healthy 인지
2) psql 로 \dt 를 실행해 테이블이 14개(13개 + cusip_map)인지
3) holdings_etf 와 cards 의 컬럼 목록(\d holdings_etf, \d cards)
실패하면 원인을 설명하고 고쳐줘. 단, db/migrations/001_init.sql 은 내가 승인하기 전엔 수정하지 마.
```

## 프롬프트 3. 스키마를 문서와 대조 검토 (15분)

```
db/migrations/001_init.sql 을 docs/기술확정안.md 와 docs/개발분담표.md 와 대조해서 검토해줘.
- 문서에 나온 컬럼/기능 중 스키마에 없는 것
- docs/conventions.md 의 규칙(티커, 날짜, 수량, chg_pct, direction)과 어긋나는 컬럼
- B(ETF 수집)와 C(카드/단계/비용 로그)가 쓰기에 부족해 보이는 컬럼
고칠 건 직접 고치지 말고 표로 제안만 해줘. 내가 고를게.
```

## 프롬프트 4. Python 워커 뼈대 확인 (15분) ★ B·C가 기다림

```
worker/ 에 Python 3.12 가상환경(.venv)을 만들고 pip install -e ".[dev]" 로 설치해줘.
그 다음 worker 폴더에서 python -m pytest -q 와 python db.py 를 실행해서 둘 다 통과하는지 보여줘.
.venv 는 git 에 올라가지 않는지도 확인해줘. 실패하면 원인을 설명하고 고쳐줘.
```

## 프롬프트 5. 13F 큰손 4명 법인 확인 (1~2시간)

```
버핏, 드러켄밀러, 피터 틸, 빌 에크먼의 13F 제출 법인을 edgartools 로 확인하려고 해.
worker/scripts/check_13f_filers.py 를 만들어줘.
- edgartools 설치(pip), .env 의 EDGAR_IDENTITY 로 set_identity 호출 (없으면 안내 메시지 출력하고 종료)
- docs/findings.md 표의 "후보 법인명"으로 검색하되, 후보가 맞는지 추측하지 말고 검색 결과를 전부 출력
  (법인명, CIK, 최근 13F-HR 제출 기간(period), 공시일, 보유 종목 수)
- 같은 이름의 다른 법인이 나오면 구분해서 보여줘
- 설치된 edgartools 버전의 실제 API 를 먼저 확인하고 써줘 (기억으로 쓰지 말고 패키지 코드/문서 확인)
실행 결과를 보여주고, 사람마다 "이 법인이 맞아 보인다/불확실하다"를 근거와 함께 알려줘.
최종 선택은 내가 하고, 내가 확정하면 docs/findings.md 와 worker/config.py 의 FILERS 에 CIK 를 반영해줘.
```

> 직접 할 일: 출력 결과를 눈으로 보고 4명 각각 맞는 법인인지 판단. 특히 피터 틸은 13F를 계속 제출하는 법인이 있는지 확인(없으면 B·C와 상의: 대체 인물 or 3명).

## 프롬프트 6. 마무리 점검과 커밋 (10분)

```
지금까지 변경 사항을 점검하고 기능 단위로 나눠 커밋해줘.
- 커밋 메시지 형식: "타입: 메시지" (예: "feat: 001_init 스키마 14개 테이블 추가")
- .env, 키가 커밋에 포함되지 않았는지 마지막으로 확인
- docs/AI_USAGE.md 에 오늘 내가 시킨 일을 줄 추가 (고친 부분은 비워 둬)
push 는 내가 할게.
```

---

# B·C에게 보낼 공지 (프롬프트 2·4 후, 복붙용)

> **[머니메이트] 레포·DB 올렸습니다**
> 1. `git clone <레포 주소>` → 폴더 이동
> 2. `cp .env.example .env` (키는 본인 것만 채우기, .env는 커밋 금지)
> 3. `docker compose up -d` → `docker compose ps` 에서 healthy 확인
> 4. 테이블 확인: `docker compose exec db psql -U moneymate -d moneymate -c '\dt'` (14개)
> 5. 읽을 문서: `CLAUDE.md`, `docs/conventions.md`
> 6. **일요일 싱크 전까지 해주세요**: 본인 테이블 컬럼이 코드에 쓸 수 있는지 확인 (B: holdings_etf — pykrx가 주는 구성종목 코드 형식 알려주기 / C: cards, steps, llm_cost_log)
> 7. 스키마 변경이 필요하면 직접 고치지 말고 저한테 요청하거나 PR로 올려주세요.
> 8. Python 쪽: `cd worker && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` (Windows는 `.venv\Scripts\activate`). edgartools 도 같이 설치됩니다
> 9. **이미 DB를 띄운 사람만** 002 적용 1회: `docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/002_13f_etf_fixes.sql` (처음 띄우는 사람은 자동 적용)
> 10. `.env` 의 `EDGAR_IDENTITY` 를 쓸 일이 있으면 **영문 이름 + naver 아닌 메일** (한글은 오류, naver.com 은 SEC가 403 거부)
> 11. Windows에서 한글이 깨지면 PowerShell에서 `$env:PYTHONUTF8=1` 먼저 실행
