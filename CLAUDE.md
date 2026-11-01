# 머니메이트 (moneymate)

뉴스로 인과 뼈대를 배우고(탭1) → 큰손의 실제 매매를 읽고(탭2) → 나만의 인과 지도로 쌓는(탭3) 모바일 웹 학습 서비스. 한 학기 캡스톤, 3명(A·B·C), 12/4 마감.
원칙: **문장은 AI가, 정답은 데이터와 코드가.** 코드가 숫자를 계산해 프롬프트에 넣고 Claude는 문장만 쓴다.

## 먼저 읽을 문서
- docs/기술확정안.md  기술·데이터·검증·채점 확정 사항
- docs/서비스흐름.md  화면 흐름
- docs/개발분담표.md      A·B·C 담당(최신). 폴더별 담당자 표시가 있다
- docs/conventions.md 공통 저장 규칙 (티커, 날짜, 수량, 방향 상수). **DB에 쓰거나 읽는 코드는 반드시 따른다**

## 구조
- worker/  Python 3.12. 수집(collectors) → 계산(compute) → 출제 에이전트·채점(generate) → 검증(validate). DB에 쓴다. 판단 채점은 FastAPI 채점 서버(judge_api.py)로 띄운다
- server/  Java + Spring Boot + MyBatis. **DB 읽기 중심**. 판단 채점·주관식 피드백은 직접 LLM을 부르지 않고 FastAPI 채점 서버에 HTTP로 요청
- web/     React + TS, 모바일 390×844
- db/migrations/  스키마 SQL. docker-compose.yml 이 PostgreSQL 16을 띄운다
- tradingagents/  탭1 해설용 시험 (별도 venv)

## 작업 규칙
1. **공통 파일은 A만 수정**: db/migrations, CLAUDE.md, docker-compose.yml, worker/config.py, worker/db.py, server의 앱 시작·DB·MyBatis 설정. 필요하면 A에게 요청하거나 PR.
2. 각자 브랜치에서 작업하고 PR로 develop에 올린다. main과 develop에는 직접 push하지 않는다. 브랜치 이름은 `타입/영어제목-이슈번호` (예: `feat/etf-collector-12`)
3. 기능마다 커밋. 커밋·PR 제목은 `타입: 메시지` (예: `feat: ETF 수집기 추가`). 타입은 feat, fix, docs, style, design, test, refactor, ci, perf, chore, rename, remove 중 하나.
   git commit · git push 는 항상 사람이 직접 한다. Claude는 실행하지 않고, 커밋 메시지 제안과 칠 명령만 알려준다. (.claude/settings.json 에서 차단)
4. 비밀값(.env, API 키)은 절대 커밋하지 않는다. 새 키 이름은 .env.example 에만 추가.
5. 스키마를 바꿔야 하면 기존 파일을 고치지 말고 `db/migrations/00N_설명.sql` 을 **새로** 만든다.
6. 겹침 계산·검증기·채점은 pytest 필수. 손계산 예시가 정답이다.
7. AI에게 시킨 일은 docs/AI_USAGE.md 에 한 줄 남긴다 (날짜·모듈·시킨 일·고친 부분).
   "고친 부분"은 사람의 판단이라 Claude가 임의로 채우지 않는다. 대화에서 사람이 AI 결과를 고치거나 거부한 것, 선택지 중 고른 것, 직접 확인한 뒤 정한 것을 **후보로 제안하고, 넣을지 물어본 뒤 승인한 것만** 적는다.
8. 모듈(파일)을 새로 만들면 docs/modules/ 에 그 모듈의 명세 초안을 함께 만든다 (한 줄 설명, 입력, 하는 일, 출력, 주의할 점, 테스트 순서로 10줄 안팎). 초안임을 파일 맨 위에 적어 둔다. 담당자가 읽고 직접 고쳐서 확정하며, 담당자가 끝까지 설명할 수 있어야 한다. 담당자가 원하면 한 칸씩 질문해서 담당자의 답을 정리하는 방식으로도 돕는다.
9. 기사 본문은 저장·게시하지 않는다. 제목·URL·언론사·시각만.
10. 매수·매도 권유, 수익 예측 표현은 어디에도 쓰지 않는다.

## 자주 쓰는 명령
```bash
cp .env.example .env              # 처음 한 번
docker compose up -d              # PostgreSQL 실행 (db 서비스)
docker compose ps                 # healthy 인지 확인
docker compose exec db psql -U moneymate -d moneymate -c '\dt'   # 테이블 목록
docker compose down               # 중지 (데이터 유지)
docker compose down -v            # 중지 + DB 초기화 (스키마를 처음부터 다시 만들 때)
docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/002_13f_etf_fixes.sql   # 이미 띄운 DB에 새 마이그레이션 1개 적용

cd worker && python -m venv .venv # 가상환경 만들기 (처음 한 번)
source .venv/bin/activate         # 가상환경 켜기 (Windows PowerShell: .venv\Scripts\Activate.ps1)
pip install -e ".[dev]"           # worker 의존성 설치 (처음 한 번, 의존성 바뀌면 다시)
cd worker && python -m pytest -q  # 워커 테스트
```

## 하지 말 것
- 숫자(주식 수, 변화율, 지표)를 LLM이 계산하게 하지 않는다. 코드가 계산한다.
- 티커·날짜·수량을 conventions.md 와 다른 형식으로 저장하지 않는다.
- 요청받지 않은 큰 리팩터링, 폴더 구조 변경을 하지 않는다.
