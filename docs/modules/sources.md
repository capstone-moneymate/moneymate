> **초안 (Claude 작성, 2026-10-28).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/collectors/sources.py (+ macro_calendar.csv)

- **한 줄 설명**: 1차 자료(DART 공시, SEC 8-K, 예정된 거시 발표)를 받아 거르기를 통과한 것만 `raw_sources`에 저장한다. 본문은 저장하지 않는다.
- **입력**: `.env` 의 `DART_API_KEY`(opendart.fss.or.kr), `ECOS_API_KEY`(ecos.bok.or.kr), `EDGAR_IDENTITY`. 날짜. 8-K는 탭 2 종목 티커 목록.
- **하는 일**: DART `list.json`에서 거래소공시(I)·주요사항보고서(B)를 페이지 끝까지 받고 유가(Y)·코스닥(K) 상장사만 `dart_category`로 거른다 (회사를 미리 고르지 않음). 8-K는 Item 2.02·1.01만, 접수 시각(acceptance)을 함께 저장. 거시 발표는 `macro_calendar.csv`에서 그날 발표를 꺼내고, 금리 전·후 값과 hike/cut/hold를 붙인다. 한은은 ECOS 722Y001(결정 당일부터 새 값), FOMC는 FinanceDataReader로 받는 FRED 목표 범위 DFEDTARU·DFEDTARL(결정 다음 날부터 새 값, 키 필요 없음). FOMC는 다음 날 아침 수집 때 FRED가 아직 안 바뀌었으면 판정이 비어서, 다음 날 같은 발표 날짜로 다시 수집해 채운다 (6주차 run_daily 에서 전날 거시 발표도 다시 돌리게 할 것). ECOS가 `RESULT` 오류(INFO-100 인증키 등)를 주면 예외로 멈추고, INFO-200(데이터 없음)만 빈 결과로 본다.
- **출력**: `Source` 목록 → `raw_sources`. 같은 (source_type, source_key)가 이미 있으면 다른 칸은 그대로 두고 `numbers`만 합친다(새 값 우선, 바뀐 게 없으면 쓰지 않음). 늦게 나온 FOMC 금리 값을 채우기 위해서다.
- **주의할 점**: DART는 접수일만 주고 시각이 없다(`published_at = NULL`) → 선별에서 당일·다음 날 둘 다 본다. `macro_calendar.csv`의 FOMC 8회와 한은 금통위 8회는 C가 federalreserve.gov·bok.or.kr 공식 일정과 대조해 날짜가 같음을 확인함(2026-10-28, verified=Y). 물가(CPI) 발표 일정은 아직 없다. 8-K 함수는 EDGAR_IDENTITY가 없어 실제 호출을 확인하지 못했다. 공통 `get_conn()`은 DB가 꺼져 있으면 오래 기다려서, 명령줄 실행은 `--save`를 붙일 때만 저장한다. 금융지주는 자회사 실적 공시("자회사의 주요경영사항")를 여러 건 내므로 같은 회사 1건 규칙(select)이 걸러 준다.
- **테스트**: `python -m pytest tests/test_sources.py -q` (DART 행 거르기·변환, 거시 일정 날짜, 금리 동결/인하 판정, FOMC는 다음 날 값으로 판정). 2026-10-28 C의 키로 실제 호출 확인: `dart 2026-10-27` → 거래소공시 186건 등에서 거르기 통과 44건(실적·공급계약·자사주·시설투자). `macro 2026-10-22` → 한은 3.00% 동결. 2026년 금통위 7회 ECOS 판정: 동결 5, 인상 2(7/16, 8/27). ECOS 주소의 줄 수가 처음엔 `/1/10/`이라 결정일 이후 값이 잘렸던 것을 실호출에서 발견해 `/1/100/`으로 고침.

## A에게 요청: 003 마이그레이션 초안 (raw_sources)

분담표 v3의 테이블 이름은 `raw_sources`인데 001에는 `raw_news`(네이버 기준)만 있다. 아래는 sources.py가 쓰는 컬럼이다. 확정과 파일 작성은 A가 한다.

```sql
CREATE TABLE raw_sources (
    id             BIGSERIAL PRIMARY KEY,
    source_type    TEXT NOT NULL CHECK (source_type IN ('dart', 'sec_8k', 'macro')),
    source_key     TEXT NOT NULL,            -- DART rcept_no / 8-K accession / 거시 event_id
    category       TEXT NOT NULL,            -- supply_contract, earnings, buyback, capex, material_agreement, fomc, bok_rate
    title          TEXT NOT NULL,
    url            TEXT NOT NULL,            -- 원문 링크
    issuer_name    TEXT,
    ticker         TEXT,                     -- 반응을 볼 대상: 국내 6자리 / 미국 티커 / 지수 키
    market         TEXT CHECK (market IN ('KR', 'US', 'INDEX')),
    published_date DATE NOT NULL,            -- 그 시장 날짜
    published_at   TIMESTAMPTZ,              -- 시각을 모르면 NULL (DART)
    numbers        JSONB NOT NULL DEFAULT '{}',  -- 카드에 쓸 숫자 (금리 전·후 등)
    collected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_type, source_key)
);
-- cards.news_id(raw_news 참조)를 cards.source_id(raw_sources 참조)로 바꾸는 것도 함께 검토
```
