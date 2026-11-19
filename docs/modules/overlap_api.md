> **초안 (Claude 작성, 2026-11-16).** 담당자 A가 읽고 고쳐서 확정한다.

# server: GET /api/overlaps, GET /api/stocks/{ticker} (com.moneymate.overlap)

- **한 줄 설명**: 탭2 겹침 메인 상단과 종목 상세(헤더·카드 ①)에 쓸 겹침 결과를 `overlap_results`에서 읽어 종목별로 묶어 돌려준다. 읽기 전용.
- **입력**: 목록은 입력 없음. 상세는 경로의 티커(앞뒤 공백 제거·대문자로 맞춤, `nvda` → `NVDA`).
- **하는 일** (`OverlapService`): ① `overlap_results`의 가장 최근 `calc_date`를 고른다 ② 그날 행을 (ticker, filer_key, etf_code) 순으로 읽고, 같은 큰손·분기·티커의 `holdings_13f`(법인명·종목명·`change_type`·공시일)와 같은 ETF·스냅샷에서 CUSIP 2~7번째 글자 = `raw_code`인 `holdings_etf`(종목명·`day_chg_pct`)를 붙인다 ③ 종목별로 큰손(`filers`)·ETF(`etfs`)는 한 번씩, (큰손, ETF) 쌍의 방향(`pairs`)은 전부 담는다.
- **출력**: 아래 예시. 변화율은 소수(0.05 = +5%), 날짜는 `YYYY-MM-DD`, `direction`(same/diff/none)과 `changeType`(new/increase/decrease/exit/unchanged)은 DB 상수 그대로이고 한글·▲▼ 변환은 화면이 한다. 겹침 결과가 아예 없으면 목록은 `{"calcDate":null,"stocks":[]}`. 상세는 최근 계산일에 그 티커가 없으면 404 `{"message": ...}`.
- **주의할 점**: 겹침·방향·임계값 판정을 서버가 **다시 하지 않는다** (정답은 `worker/compute/overlap.py`). 그래서 "N명 늘림"은 내려주지 않는다(아래 부족한 점). `overlap_results`는 ETF가 기준일이나 최신에 가진 종목만 있어 ETF가 없는 13F 종목(예: buffett AAPL)은 목록에 없다. ETF가 최신 스냅샷에서 전량 정리했으면 `dayChgPct`·`etfStockName`이 null이다. `holdings_etf.ticker`는 NULL일 수 있어 JOIN에 쓰지 않는다(P16).
- **테스트**: `cd server; .\gradlew.bat test`. `OverlapServiceTest`(가짜 DB 5개: 빈 목록, 묶기, 티커 대문자, 404 두 경우), `OverlapApiIntegrationTest`(Testcontainers PostgreSQL 16 + 001~003 + `src/test/resources/fixtures/overlap.sql`, 응답 JSON 전체를 STRICT 비교 4개). **Docker가 꺼져 있으면 통합 테스트는 건너뛴다(skipped).** fixture의 겹침 행은 같은 입력을 `overlap.build_results`에 넣은 결과와 같다 (손계산: KoAct NVDA 99.88 → 104.874 = +0.05, TIME 239 → 200 = -0.16318).

## 응답 예시 (fixture 기준)

`GET /api/overlaps`

```json
{
  "calcDate": "2026-11-14",
  "stocks": [
    {
      "calcDate": "2026-11-14", "ticker": "GOOGL",
      "issuerName": "ALPHABET INC", "etfStockName": "ALPHABET INC-CL A",
      "filers": [{"filerKey": "ackman", "filerName": "Pershing Square Inc.", "changeType": "decrease",
                  "chgPct": -0.25, "periodEnd": "2026-06-30", "filedAt": "2026-08-14"}],
      "etfs": [{"etfCode": "0015B0", "snapshotDate": "2026-11-13", "trendChgPct": 0.1, "dayChgPct": 0.0}],
      "pairs": [{"filerKey": "ackman", "etfCode": "0015B0", "direction": "diff"}]
    },
    { "calcDate": "2026-11-14", "ticker": "NVDA", "...": "아래 상세와 같음" }
  ]
}
```

`GET /api/stocks/NVDA`

```json
{
  "calcDate": "2026-11-14", "ticker": "NVDA",
  "issuerName": "NVIDIA CORPORATION", "etfStockName": "NVIDIA CORP",
  "filers": [
    {"filerKey": "druckenmiller", "filerName": "Duquesne Family Office LLC", "changeType": "increase",
     "chgPct": 0.1, "periodEnd": "2026-06-30", "filedAt": "2026-08-14"},
    {"filerKey": "thiel", "filerName": "Thiel Macro LLC", "changeType": "new",
     "chgPct": null, "periodEnd": "2026-06-30", "filedAt": "2026-08-13"}
  ],
  "etfs": [
    {"etfCode": "0015B0", "snapshotDate": "2026-11-13", "trendChgPct": 0.05, "dayChgPct": 0.01},
    {"etfCode": "426030", "snapshotDate": "2026-11-13", "trendChgPct": -0.16318, "dayChgPct": -0.02}
  ],
  "pairs": [
    {"filerKey": "druckenmiller", "etfCode": "0015B0", "direction": "same"},
    {"filerKey": "druckenmiller", "etfCode": "426030", "direction": "diff"},
    {"filerKey": "thiel", "etfCode": "0015B0", "direction": "same"},
    {"filerKey": "thiel", "etfCode": "426030", "direction": "diff"}
  ]
}
```

`GET /api/stocks/AAPL` → 404 `{"message": "겹침 결과에 없는 종목입니다: AAPL"}`

```bash
curl -s localhost:8080/api/overlaps
curl -s localhost:8080/api/stocks/NVDA
```

## 부족한 점 (컬럼에 없어 내려주지 않는 값)

| 화면 | 필요한 값 | 현재 |
|---|---|---|
| 메인 상단 | "큰손 4명 중 2명 이상 함께 늘린 종목", "N명 늘림" | `overlap_results`에 ETF가 없는 종목은 없다. 큰손별 늘림/줄임 판정(임계값 5%)은 저장되지 않아 서버가 세면 재계산이 된다 |
| 메인·카드 ① | 큰손별 ▲▼, ETF별 ▲▼ | `direction`은 비교 결과만 있다. 원값(`changeType`, `chgPct`, `trendChgPct`)만 내려준다 |
| 카드 ① | ETF 추세 기준일 | `overlap_results`에 없다 (`holdings_etf.trend_base_date`는 B 값이라 overlap.py 기준일과 다를 수 있음) |
| 카드 ① | "기록 없음" 큰손 | 4명 목록은 `worker/config.py FILERS`에만 있다. `filers`에 없는 큰손이 기록 없음 |
| 헤더 | 섹터 태그, 성격 태그, 회사 한 줄 소개 | 어떤 테이블에도 없다 |
| 헤더 | 한글 종목명 | `issuer_name`(13F 영문), `stock_name`(pykrx 표기)뿐 |
| 메인 하단 | 변동성 TOP2 | `prices`에서 계산해야 한다 (이 API 범위 밖) |
| 카드 ②③ | 이유, 지금은 | #101에서 상세 응답 `reasons`로 연결했다(아래) |
| 13F 공시 전 | 안내문 상태 | 공시 전/후 1~2주/그 이후 구분 값 없음 (`filedAt`으로 화면이 판단 가능) |

## 스키마 변경 제안 (적용하지 않음. 004는 stock_reasons 로 썼으므로 다음 번호)

```sql
ALTER TABLE overlap_results
    ADD COLUMN big_dir        TEXT CHECK (big_dir IN ('up', 'down')),   -- overlap.big_direction 결과, 판단 안 하면 NULL
    ADD COLUMN etf_dir        TEXT CHECK (etf_dir IN ('up', 'down')),   -- overlap.etf_direction 결과
    ADD COLUMN etf_status     TEXT CHECK (etf_status IN ('held', 'new', 'exit')),
    ADD COLUMN etf_base_date  DATE;                                     -- ETF 추세 기준 스냅샷 (P7·P15)
```

- `big_dir`가 있으면 "N명 늘림"을 서버가 `count(*) FILTER (WHERE big_dir = 'up')`로 **세기만** 하면 된다(판정은 worker 한 곳).
- ETF가 없는 13F 종목까지 메인 상단에 보이려면 overlap.py `co_held()` 결과를 저장할 테이블(예: `co_held(calc_date, big_period_end, ticker, filer_keys TEXT[])`)이 필요하다. (#172에서 `co_increased()` → `co_held()`, 기준은 2명 이상 보유)
- 종목 헤더의 섹터·성격·소개는 `stock_profiles(ticker PK, name_ko, sector, style, intro)` 같은 정적 테이블을 제안한다(손으로 채움).

## "내 지도에 있어요" 조회 (#100, #101에서 상세 응답 `myConcepts`로 연결)

`OverlapService`에 메서드 두 개를 두고, SQL은 `OverlapRepository.xml`의 `findMyMapTickers`·`findMyConceptsForTicker`에 있다. 아직 엔드포인트에는 연결하지 않았다.

- `myMapTickers(userId)`: 사용자가 배운 개념(`user_concepts.total > 0`)과 `concept_tickers`로 연결된 종목들이다. 티커 순이고, 종목마다 개념 목록(id·이름·테마)이 붙는다. 겹침 메인의 배지용이다.
- `myConceptsForTicker(userId, ticker)`: 종목 하나에 연결된 개념 중 사용자가 배운 것이다. 티커는 대문자로 맞춘다. 종목 상세용이다.
- 기록이 없는 사용자나 처음 보는 사용자는 빈 목록이다. 팀 검토 전이라 `status`는 거르지 않는다. userId는 UUID 문자열이다. 형식이 틀리면 DB 오류가 나므로, API에 붙일 때 마이페이지처럼 400으로 막는다.
- 테스트: `OverlapMyMapIntegrationTest` 3개(Testcontainers + `fixtures/my_map.sql`, 손계산은 fixture 맨 위에 있다), `OverlapServiceTest`에 2개를 추가했다.

## 종목 상세의 카드 ②③과 "내 지도에 있어요" (#101)

`GET /api/stocks/{ticker}?userId=<UUID>`. userId는 선택이고, UUID가 아니면 400이다. 응답은 위 상세에 두 칸을 더한다.

- `reasons`: `stock_reasons`에서 그 티커의 `status = 'published'` 중 가장 최근 `big_period_end` 한 줄이다(P19). 없거나 JSON이 깨졌으면 `null`이고, 화면은 대체 문구를 보여 준다. C가 저장한 snake_case JSON(`docs/modules/reasons.md` "저장 모양")을 서버가 camelCase로 옮긴다. 이유를 만들거나 고치지 않고, 아래 두 가지만 더한다.
  - 경로 개념마다 `concepts.name`과 `learned`(사용자가 배운 개념, `user_concepts.total > 0`)를 붙인다. 사전에 없는 id는 이름 대신 id를 쓴다.
  - 이유마다 `side`를 그대로 옮긴다(2026-11-19 B). 큰손과 ETF가 반대로 움직인 종목은 `big`(큰손 쪽, 분기 말 이전 근거) / `etf`(ETF 쪽, 분기 말 이후 근거)이고, 그 밖과 예전 저장분은 null이다(reasons.md "양쪽 이유").
  - 이유마다 `inMyMap`(경로에 배운 개념이 하나라도 있음)을 붙인다.
  - 화면용이 아닌 값은 내보내지 않는다: `start_concept`·`end_concept`(경로에 있음), 근거의 `source_id`, 카드 ③의 `errors`, `model_info`.
- `reasons.now`: 카드 ③이다. `now_view`가 NULL이면 `null`이다. `price.returnPct`는 C가 저장한 퍼센트 값 그대로다(12.5 = 12.5%). conventions P2(변화율은 소수)와 다르니 C에게 확인할 안건이다.
- `reasonsRejected` (#164): `reasons`가 null이고, 그 티커의 가장 최근 분기 `stock_reasons` 줄이 `rejected`면 true다(`findLatestReasonsStatus`). C의 #161에서 방향이 맞는 이유가 하나도 없으면 rejected로 저장하므로, 화면은 "준비 중" 대신 "공개된 자료로는 설명할 이유를 찾지 못했어요." 고정 문구를 보여 준다. 줄이 없거나 pending이면 false다. 예전 분기만 rejected이고 최근 분기를 아직 안 만들었을 때도 false다. published 이유를 보여 주는 중이면 상태를 묻지 않고 false다.
- `myConcepts`: #100 매핑(`concept_tickers`)으로 이 종목과 연결된 개념 중 사용자가 배운 것이다. userId가 없으면 빈 목록이다.

```json
"reasons": {
  "bigPeriodEnd": "2026-06-30", "direction": "diff", "change": "up", "headline": "왜 방향이 다를까요?",
  "reasons": [{"title": "AI 투자 확대", "body": "…", "direction": "up", "inMyMap": true,
    "path": [{"id": "ai_investment", "name": "AI 데이터센터 투자", "learned": false},
             {"id": "gpu_demand", "name": "AI 반도체 수요", "learned": true}],
    "evidence": [{"no": 4, "publishedDate": "2026-06-12", "title": "…", "issuerName": "…", "url": "https://…"}]}],
  "now": {"baseDate": "2026-06-30",
    "price": {"fromDate": "2026-06-30", "fromClose": 100.0, "toDate": "2026-11-14", "toClose": 112.5, "returnPct": 12.5},
    "laterSources": [{"publishedDate": "…", "title": "…", "url": "…", "numbers": {"매출액 전년동기대비(%)": 62.0}}],
    "linked": [{"conceptId": "gpu_demand", "name": "AI 반도체 수요", "reasonTitle": "AI 투자 확대"}],
    "text": null}
},
"myConcepts": [{"id": "gpu_demand", "name": "AI 반도체 수요", "theme": "AI·반도체"}]
```

- 테스트: `OverlapApiIntegrationTest` 6개.
  - NVDA는 더 최근 분기의 pending과 오래된 published를 건너뛰고 2026-06-30 published를 내준다. userId가 없으면 learned가 false이고 `myConcepts`가 빈 목록이다. userId가 있으면 learned·inMyMap이 true이고 `myConcepts`가 채워진다. 카드 ③의 errors는 나오지 않는다.
  - GOOGL은 rejected만 있어서 `reasons`가 null이고 `reasonsRejected`가 true다. NVDA는 false다.
  - userId가 `abc`이면 400이다.
- 테스트: `OverlapServiceTest` 14개. #164에서 3개를 추가했다: 최근 분기 rejected면 true, 줄 없음·pending이면 false, published가 있으면 상태를 묻지 않고 false. 나머지 11개는 이름·learned 붙이기, 사전에 없는 id, 개념 id를 한 번씩만 조회하는지, userId가 없으면 조회하지 않는지, 이유는 없지만 `myConcepts`는 있는 경우, 깨진 JSON이면 null.
