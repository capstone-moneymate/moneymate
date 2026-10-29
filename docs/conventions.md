# 공통 저장 규칙 (conventions.md)

> 상태: **초안 v0.1** (작성 A, 2026-10-10). 10/11(일) 밤 싱크에서 확정한다.
> 근거: docs/개발분담표.md 7장. 수집기를 셋이 나눠 만들기 때문에 이 규칙이 어긋나면 겹침 계산과 화면 연결에서 문제가 생긴다.
> 이 문서와 db/migrations 가 다르면 **이 문서를 먼저 고친 뒤** 마이그레이션을 새로 만든다.

## 1. 확정 대상 규칙 (분담표 7장 표)

| 항목 | 규칙 | 예 | 컬럼 |
|---|---|---|---|
| 미국 티커 | 대문자, 클래스주는 하이픈 | `NVDA`, `BRK-B` | `ticker` |
| 한국 종목·ETF | 6자리 코드 **문자열**(숫자 아님, 앞자리 0 유지). 영문 대문자가 섞일 수 있음 | `'426030'`, `'0015B0'`, `'00104K'` | `etf_code`, `ticker` |
| 시장 날짜 | 그 시장의 거래일, `DATE` | 미장 10/8 종가는 `2026-10-08` | `market_date`, `snapshot_date` |
| 수집 시각 | `TIMESTAMPTZ`(UTC 저장), 화면에서 KST로 표시 | | `collected_at` |
| 13F 날짜 | 분기 말과 공시일을 **따로** 저장 | | `period_end`, `filed_at` |
| 수량 | 주식 수 `BIGINT`, **비중은 저장하지 않음**. ETF 수량은 1CU(설정 단위) 기준이라 소수 가능 → `holdings_etf.shares`만 `NUMERIC` (003) | KoAct NVIDIA `99.88` | `shares` |
| 변화율 | 소수 `NUMERIC` (0.05 = +5%) | | `chg_pct` |
| 방향 | 영어 상수 3개, 화면에서 한글로 바꿈 | `same` / `diff` / `none` | `direction` |

## 2. 이 표에서 비어 있어 A가 제안하는 것 (싱크에서 O/X 결정)

| # | 제안 | 이유 |
|---|---|---|
| P1 | **티커 정규화는 저장 직전 한 곳에서.** 공백 제거 → 대문자 → 미국 티커의 `.`는 `-`로 (`BRK.B` → `BRK-B`). 한국 코드는 대문자로 바꾸고, 숫자만이면 `str.zfill(6)`, 영문이 섞였으면 6자리 그대로(0 채우지 않음) | 출처마다 표기가 달라 JOIN이 어긋나는 것을 막는다. `worker/common/normalize.py` 한 함수로 A가 제공, B·C는 가져다 쓴다 |
| P2 | **변화율 계산식 고정**: `chg_pct = (shares_now - shares_prev) / shares_prev`. 이전 값이 0이거나 없으면 `NULL` (0이나 ∞ 넣지 않음) | 신규 편입을 "무한대 증가"로 오해하지 않게 |
| P3 | **방향 판정 기준**: 큰손 `chg_pct`와 ETF 추세(`trend_chg_pct`, 분기 말 대비)의 부호가 같으면 `same`, 반대면 `diff`. 한쪽이 없거나 기준 미만이면 `none`. 기준값 N%는 2주차 확정 (신규 편입 new 는 P13 참조) | `none`의 의미를 미리 정해 둔다 |
| P4 | **"늘림" 임계값은 코드 상수 한 곳**(`worker/config.py`의 `INCREASE_THRESHOLD`, 임시 0.05)에서만 정의 | 2주차에 숫자만 바꾸면 되게 |
| P5 | **13F 필터**: `shares` 는 SharesPrnAmount 중 주식(SH)만, 옵션(PUT/CALL)과 채권(PRN)은 저장 전에 제외 | 기술확정안 데이터 수집 표 |
| P6 | **ETF 스냅샷 기준 시점**: 한 번 받은 날짜의 데이터는 덮어쓰지 않는다 (`UNIQUE(etf_code, snapshot_date, raw_code)`, 재수집은 `ON CONFLICT DO NOTHING`). `source` 컬럼에 출처 기록 | 반자동으로 바뀌어도 출처가 남게 |
| P7 | **기준일 규칙**: 겹침 비교는 "13F 분기 말(`period_end`)"과 "ETF의 같은 분기 말 대비 최신 스냅샷"만 비교. 날짜가 다른 값을 암묵적으로 섞지 않는다 | 분담표 3·5장의 "같은 시점 기준" |
| P8 | **카드 상태**: `status` ∈ `pending / published / rejected`. 서버는 `published` 만 내려준다 | 기술확정안 8단계 게시 |
| P9 | **`user_id`**: UUID(브라우저 생성). 서버가 처음 보면 `users`에 넣는다 | 기술확정안 사용자 식별 |
| P10 | **시간대**: 코드 안에서 시각은 항상 timezone-aware(UTC)로 다룬다. 미국장 날짜(`market_date`)와 KST 날짜의 차이는 주석으로 명시한다 | 기술확정안 "시간대" |
| P11 | **LLM 숫자 규칙**: LLM 출력의 숫자는 신뢰하지 않고 코드가 재계산한 값으로 덮어쓴다 | "정답은 데이터와 코드가" |
| P12 | **13F 전량 매도**: 직전 분기에 있었는데 이번 분기 13F에서 사라진 종목은 행을 만들어 `shares=0`, `chg_pct=-1`, `change_type='exit'` 로 저장한다 (002) | 행이 없으면 "줄임 ▼"(-100%)을 보여줄 수 없다 |
| P13 | **13F 변화 종류 `change_type`**: `new`(직전 분기에 없음) / `increase` / `decrease` / `unchanged`(수량 비교, 임계값과 무관) / `exit`(P12). 방향 판정에서 **`new`는 "늘림"으로 처리**한다 (`chg_pct`가 NULL이어도 P3의 `none`으로 보내지 않음). "늘림" 임계값(P4)은 `increase`에만 적용 (002) | P2로 신규 편입의 `chg_pct`가 NULL이라 새로 산 종목이 빠지는 것을 막는다 |
| P14 | **13F 같은 CUSIP 합산**: 한 제출 건에 같은 CUSIP이 여러 줄이면(운용 주체 구분 등) P5 필터 후 `shares` 를 합산해 한 줄로 저장한다 | `UNIQUE(filer_cik, period_end, cusip)` 충돌, 수량 누락 방지 |
| P15 | **ETF 추세 기준일**: `trend_chg_pct` 를 계산할 때 비교한 스냅샷 날짜를 `holdings_etf.trend_base_date` 에 저장한다. 보통 13F 분기 말, 그날 스냅샷이 없으면 수집 시작일 (002) | P7 "날짜를 섞지 않는다"를 데이터로 확인할 수 있게 |
| P16 | **ETF 구성종목 코드·저장 범위**: pykrx 구성종목 코드는 CUSIP 9자리의 2~7번째 글자다(NVIDIA `67066G104` → `7066G1`). `raw_code`에 받은 그대로 저장하고, `ticker`는 13F `cusip`의 2~7번째 글자와 맞추거나 OpenFIGI로 변환해 채운다(못 찾으면 `NULL`). **주식만 저장**하고 원화현금 `010010`, 설정현금액 `H00000`, 선물은 저장하지 않는다. 1CU 기준 수량이라 **자금 유입 보정(`trend_adj_pct`)은 쓰지 않는다** (003) | findings.md B칸. 6자리가 드물게 다른 회사와 겹칠 수 있어 매칭 결과는 종목명으로 한 번 확인한다. 운용사가 설정 단위를 바꾸면 전 종목이 같은 비율로 변하므로 수집기가 경고한다 |
| P17 | **판단 단계 "맞음" 기준**: 판단(`judgement`) 채점 `score`(0~100) **60점 이상**이면 `user_concepts`에 맞음으로 기록한다. 기록은 공통 함수 `recordConceptResult(userId, conceptIds, isCorrect)` 하나로 (B 구현, answers.ts·judgement.ts가 부름) | 채점이 두 곳에서 일어나도 기준이 하나가 되게 |
| P18 | **카드 출처**: 카드는 `card_sources`(card_id, source_id, is_main)로 `raw_sources`의 1차 자료 여러 개를 묶는다. 대표 자료(`is_main`)는 카드당 1개. `cards.news_id`는 없앴다 (003) | 같은 사건 자료를 한 카드로 묶되 FK로 무결성 유지 |

## 3. 컬럼 합의가 필요한 5개 테이블 (분담표 7장)

`db/migrations/001_init.sql` + `002_13f_etf_fixes.sql` + `003_etf_sources_cards.sql` 기준. **B는 holdings_etf, C는 cards·steps, A는 holdings_13f·overlap_results 를 보고 "내 코드가 이 컬럼으로 읽고 쓸 수 있는지" 확인한다.**

| 테이블 | 쓰는 사람 → 읽는 사람 | 확인할 점 |
|---|---|---|
| holdings_13f | A → A(overlap), 탭2 | `filer_key`가 4명 구분. `chg_pct`는 A가 채움 |
| holdings_etf | B → A(overlap), B(trend) | 확인됨: 구성종목 코드는 CUSIP 2~7번째 글자 → `raw_code`, `ticker`는 변환 후 채움 (P16) |
| overlap_results | A → 탭2 | `direction` 3값, 사용한 두 기준일 저장 |
| cards | C → 탭1 | `card_type` 1/2/3, `key_facts`(채점 증거용), `status`, 출처는 `card_sources` (P18) |
| steps | C → 탭1, A(채점) | `kind` 5종(concept, quiz, causal_order, chart, judgement. AI 분석은 judgement 결과 화면이라 단계가 아님), `answer`는 서버가 사용자에게 내려보내지 않음 |

## 4. 마이그레이션

- 파일명: `db/migrations/NNN_설명.sql` (NNN은 3자리 순번). 이미 올라간 파일은 **고치지 않는다.**
- 빈 DB는 `docker compose up` 시 자동 적용된다. 이미 만든 DB에는 자동으로 다시 적용되지 않는다.
  - 새 파일 하나만 적용: `docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/002_xxx.sql`
  - 처음부터 다시: `docker compose down -v && docker compose up -d` (데이터 삭제됨. 수집 중인 ETF 데이터가 있으면 먼저 백업)
- 스키마 변경은 A에게 요청한다 (공통 파일).

## 5. 결정 기록

| 날짜 | 결정 | 결정한 사람 |
|---|---|---|
| 2026-10-10 | 전량 매도 종목은 `shares=0`, `chg_pct=-1`, `change_type='exit'`로 저장 | A (싱크에서 확정 예정) |
| 2026-10-10 | `holdings_13f.change_type`, `holdings_etf.trend_base_date` 추가 (002) | A (싱크에서 확정 예정) |
| 2026-10-29 | 003: `holdings_etf.shares` NUMERIC, `raw_code` 추가·UNIQUE 변경, `trend_adj_pct` 제거(방향 판정은 `trend_chg_pct`), `normalize_kr_code` 영문 허용 | B 요청, A 반영 |
| 2026-10-29 | 003: `raw_sources`·`card_sources` 추가, `cards.news_id` 삭제, `steps.kind`에서 `open_ended`·`ai_analysis` 삭제, 루브릭 9점 주석 | B·C 요청, A 반영 |
| 2026-10-29 | 판단 단계 60점 이상을 맞음으로 기록 (P17) | A |
