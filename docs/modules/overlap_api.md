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
| 카드 ②③ | 이유, 지금은 | 004에서 `stock_reasons` 표를 만들었다(C 요청, P19). reasons.py 저장과 이 API 응답 연결은 C가 JSON 모양을 정리한 뒤(#101) |
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
- ETF가 없는 13F 종목까지 메인 상단에 보이려면 overlap.py `co_increased()` 결과를 저장할 테이블(예: `co_increased(calc_date, big_period_end, ticker, filer_keys TEXT[])`)이 필요하다.
- 종목 헤더의 섹터·성격·소개는 `stock_profiles(ticker PK, name_ko, sector, style, intro)` 같은 정적 테이블을 제안한다(손으로 채움).
