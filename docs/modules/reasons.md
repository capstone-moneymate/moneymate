> **초안 (Claude 작성, 2026-11-15).** 담당자 C가 읽고 고쳐서 확정한다. 5주차 시작본. 6주차: 카드 ③은 stock_now.py(docs/modules/stock_now.md), 저장은 save()(A의 004 `stock_reasons`, conventions P19). 실행: 분기마다 `scripts/run_reasons.py`(docs/modules/run_reasons.md), 카드 ③은 run_daily "탭2 지금은" 단계가 매일 갱신. 근거 검사는 B의 `check_evidence`(#130). 남은 것: A의 `/api/stocks/{ticker}` 응답 연결(#101).

# worker/generate/reasons.py

- **한 줄 설명**: 탭 2 종목 상세 카드 ② "이유 (AI 추정)"를 만든다. 큰손·액티브 ETF가 왜 늘리거나 줄였을지 1~3개 이유를 쓰고, 이유마다 인과 뼈대와 근거 자료(날짜 포함)를 붙인다.
- **입력**: 종목(`ticker`, `name`), A의 `overlap_results.direction`(`same`·`diff`·`none`)과 큰손 쪽 변화(`up`·`down`), 공시 기준일(13F 분기 말), 카드 ① 숫자 문장(코드가 만든 것), 근거 후보. 근거 후보는 `load_evidence`가 `raw_sources`에서 그 종목 자료와 **같은 시장의** 거시 발표(미국 종목은 US500·IXIC 키의 FOMC 등, 국내 종목은 KS11·KQ11 키의 한은 등) 중 기준일 앞 92일 안(기준일 포함)에 나온 것을 최근 순으로 20개까지 번호를 붙여 고른다. 근거마다 `numbers`(거시 decision·금리 전후, DART 증감률 등, 중요한 값 8개, 일정 확인 칸 제외)도 프롬프트에 넘기고 저장할 때는 뺀다. 실행은 `cd worker && python -m generate.reasons NVDA 2026-09-30 same up "드러켄밀러 +24%"`.
- **하는 일**: ① 제목은 방향으로 코드가 정한다(같은 방향 늘림 "왜 다 늘렸을까요?", 줄임 "왜 다 줄였을까요?", 다름 "왜 방향이 다를까요?", 한쪽만 "왜 늘렸을까요?"). ② Sonnet 1회 호출(effort medium, `llm_client`로 비용 기록, module=`reasons`). 개념 id와 근거 번호를 JSON 스키마 enum으로 묶어 사전·입력 밖의 값은 나올 수 없다. ③ 코드 검사: 이유 1~3개, 근거 번호 1개 이상·입력에 있음·같은 번호 두 번 아님·날짜가 기준일 이전(B의 `validators.check_evidence`, #130), 시작≠끝이고 사전에 경로가 있음, 경로마다 방향이 다른 모호한 쌍이 아님(graph.py 규칙, #85 리뷰), 금지 표현(B의 `find_banned`). ④ 걸리면 이유를 돌려주고 1번 더 쓰게 한다. 그래도 걸리면 혼자 검사해서 통과하는 이유만 살리고 뺀 까닭은 `dropped`(model_info.dropped)에 남긴다(사전에 없는 경로 하나 때문에 종목 전체가 rejected 되던 문제, 2026-11-16). ⑤ 방향 경고(`direction_warnings`): 큰손이 한쪽으로 움직인 종목(same·none)에서 이유의 힘이 큰손 변화와 반대면 "큰손 방향과 맞는 경로만 골라" 한 번 다시 쓰게 하고(`MAX_DIRECTION_RETRIES` = 1), 그래도 반대인 이유는 빼서 `warnings`에 남긴다. 하나도 안 남으면 errors("큰손 변화와 방향이 맞는 이유가 없어요") → `rejected`(2026-11-18 B 제안. 11-16~17에는 `pending`으로 두고 사람이 봤다). diff 종목은 보지 않는다. ⑥ 금리 사건 개념(B 결정 2026-11-16): `rate_hold`는 이유의 시작 개념에서 뺀다(스키마 enum, `NOT_START`). `rate_hike`·`rate_cut`은 근거에 실제 그 결정(numbers.decision = hike·cut)이 있고 change가 up일 때만 시작 개념이 된다(`DECISION_EVENTS`, 어기면 다시 쓰게 함). 끝 개념으로는 쓸 수 있다.
- **출력**: `ReasonsResult(headline, reasons, errors, calls, warnings)`. 이유마다 `title`, `body`, `start_concept`, `change`(시작 개념의 변화: 커짐·일어남 up / 줄어듦 down, LLM이 enum으로 고름. 5주차 노션 제안 (1)), `end_concept`, `path`(B의 graph.py로 찾은 가장 짧은 사전 경로), `direction`(시작 개념이 change 했을 때 끝 개념이 받는 힘 up ▲ / down ▼, `graph.effect(g, start, end, change)`로 코드가 계산. 화면 표시용), `evidence`(번호·`raw_sources.id`·날짜·제목·발표 기관·URL). 끝내 통과하지 못하면 `reasons`가 비고 `errors`에 마지막 이유가 남는다. 근거 후보가 없으면 API를 부르지 않는다.
- **주의할 점**: 이유는 추정이다. 근거 번호를 고른 것이 그 자료가 이유를 증명한다는 뜻은 아니다. 숫자는 카드 ①과 근거의 제목·numbers에 있는 것만 쓰게 했지만 문장 속 숫자를 코드가 다시 확인하지는 않는다. 2026-11-16 2분기 20종목 실데이터: 근거로 제목만 넘겼을 때는 FOMC 동결을 "금리 부담이 줄었다"로 지어내고 미국 종목에 한은 결정이 들어갔다 → numbers 전달과 시장 필터 뒤에는 "FOMC가 4월과 6월 모두 3.75%로 동결"처럼 사실대로 쓴다. 이유가 사전 경로 두 가지(rate_hold → growth_valuation, corp_earnings → eps)로 반복되고(근거가 8-K 제목·FOMC뿐이고 8-K는 numbers가 없음), same·none 종목 이유 22개 중 11개는 경로 방향이 큰손 변화와 반대였다. 시작 개념 change를 받은 뒤 다시 생성하면($0.29) 반대가 6개로 줄었다: "순이익이 줄어 줄였다"는 corp_earnings(down) → eps ▼로 맞게 계산된다(6개). 남은 6개는 모두 늘린 종목에 붙은 "금리 동결(up) → 성장주 가치평가 ▼"였다. B 결정으로 rate_hold를 시작 개념에서 뺐더니 2분기(4/29·6/17 모두 동결) 20종목 중 18곳에서 동결을 rate_hike(down)·rate_cut(down)으로 돌려 썼다 → 실제 결정이 있을 때만 쓰게 막은 뒤 다시 생성: 금리 이유 0, 방향 경고 0, 17 published·3 rejected(ARM·TSM 쓸 이유 없음, BE 사전에 없는 경로). 이유가 대부분 "8-K 실적 발표 → 기업 순이익"(16/19) 하나라 얇다. 8-K는 제목만 있어 "공시 내용은 알 수 없지만"이라고 쓴다 → 8-K에 SEC XBRL 분기 실적을 붙였다(collectors/sec_numbers.py). 다시 생성하면 이유가 숫자를 근거로 쓰지만("당기순이익이 전년 동기보다 60.9% 늘었다") LLM이 사전에 없는 revenue → eps·corp_earnings 경로를 골라 11곳이 통째로 rejected → 통과한 이유만 살리게 바꾼 뒤: 12 published·3 pending·5 rejected, 이유 16개 모두 증감률 인용. pending 3곳(MU·AAPL·COHR)은 "호실적 뒤 차익 실현"(순이익 ▲인데 줄임)이었고, B와 검토해 사전 밖 설명(투자자 행동, 1차 자료로 방향 확인 불가)이라 rejected로 정했다(2026-11-18). rejected는 revenue → corp_earnings·eps 경로가 사전에 없음 3곳(B에게 요청), 해외 발행사라 8-K가 없음 2곳(ARM·TSM). 기사 본문은 넘기지 않고 제목만 쓴다(CLAUDE.md 9). 근거 날짜 검사는 #85에서 약속한 대로 B의 근거 날짜 검증기(`check_evidence`, #130)로 바꿨다(2026-11-17). 오류 문장은 예전과 같고, 같은 근거 번호를 두 번 고르면 새로 걸린다. 방향 경고는 끝 개념이 "커지면 늘릴 이유"라고 가정한다. 비용·금리처럼 커지면 줄일 이유인 끝 개념은 경고가 거꾸로 나올 수 있어서 거부하지 않는다(사전에 그 정보가 없음). 금리 뉴스와 AI 테마는 #67 이후 사전에서 이어지지 않아 그런 이유는 경로 검사에서 걸린다.
- **테스트**: `cd worker && python -m pytest tests/test_reasons.py -q` (가짜 응답: 방향 반대면 한 번 다시 쓰기·그래도 반대인 이유만 빼기·하나도 없으면 rejected·엇갈린 종목은 다시 쓰지 않음, save 에 pending 없음, 방향별 제목 4가지, 정상 이유와 코드가 찾은 경로, 스키마 enum, 프롬프트 JSON 묶기, 불량 8가지(모호한 쌍 포함), 누르는 힘 경로의 방향, 기준일 뒤 근거, 금지 표현, 수정 1회 후 통과, 수정 상한, 근거 없으면 호출 안 함, 잘린 응답, change 가 down 이면 방향이 뒤집혀 줄임과 맞음, change 칸 없는 예전 응답은 up·경고, diff 는 경고 안 함, rate_hold 는 시작 enum 에서 빠지고 끝 enum 에는 남음, rate_hike 는 근거에 hike 결정이 있고 change up 일 때만, 고쳐 쓰기 뒤에도 걸리면 통과한 이유만 살리고 dropped 에 남김). 양쪽 이유 테스트(2026-11-19): `etf_change` 손계산 5가지(새로 담음 +1, 5% 미만 안 셈, 1:1이면 합의 부호, ETF마다 한 번), `is_split` 4가지(3분기 AMD는 나눔, MSFT는 안 나눔), 번호 다시 붙이기, 쪽마다 근거 기간 검사, 두 쪽 모두 통과(ai_investment → semi_earnings (+1)(+1): 큰손 down → ▼, ETF up → ▲), ETF 쪽 방향이 반대면 한 번 다시 쓰고 그 쪽만 뺌, 빠진 쪽은 한 번 더 물음, ETF 쪽 근거가 없으면 묻지 않음, missing_sides·side 저장과 예전 저장분 읽기. 저장 status 는 `tests/test_stock_now.py`(경고 있으면 pending). 저장·종목 방향은 `tests/test_stock_now.py`(published·rejected upsert 인자, 방향 규칙 손계산). 2026-11-16 로컬 DB에 004 적용 뒤 시험 줄을 published → rejected로 두 번 저장해 한 줄 덮어쓰기 확인, 시험 줄은 지움. 실데이터(2분기 20종목) 확인은 docs/modules/run_reasons.md.

## 양쪽 이유 (2026-11-19 B, 8주차)

**왜**: 13F는 분기 말(9/30) 기록이고 ETF 추세는 그 뒤(9/30 → 11/18)다. 근거를 기준일 이전 자료만 쓰면, 큰손과 ETF가 반대로 움직인 종목에서 ETF가 왜 다르게 움직였는지 설명할 재료가 없다. 그래서 "왜 방향이 다를까요?"라고 묻고 한쪽만 설명했다. 3분기 diff 9종목 중 7종목이 큰손 줄임 vs ETF 늘림이었다.

**언제 나누나** (`is_split`): `direction`이 diff이고, ETF 쪽 변화(`etf_change`)가 큰손 쪽 변화(`change`)와 반대일 때만 나눈다.
- `etf_change`: ETF마다 한 번씩 센다. 새로 담음(NULL)은 +1, 모두 정리는 -1.0이고, ±`ETF_TREND_THRESHOLD`(5%) 미만은 세지 않는다. 많은 쪽을 고르고, 같으면 합의 부호다.
- diff라도 큰손끼리만 엇갈리고 ETF가 큰손 다수와 같은 쪽이면 예전처럼 한쪽 이유다. 3분기 MSFT(애크먼 줄임·틸 신규, ETF 늘림)와 SPCX(ETF끼리 엇갈림)가 그렇다.

**하는 일**:
- **근거**: 큰손 쪽은 지금처럼 `load_evidence`(기준일 앞 92일)를 쓴다. ETF 쪽은 `load_etf_evidence`로 기준일 다음 날 ~ ETF 최신 스냅샷(`overlap_results.etf_snapshot_date`) 자료를 읽는다. `split_evidence`가 둘을 한 목록으로 합쳐 큰손 쪽 1..n, ETF 쪽 n+1..로 번호를 다시 붙이고 근거마다 `side`를 적는다.
- **프롬프트·스키마**: 시스템 프롬프트에 `split_rules`(두 기간, side 고르기, 그 쪽 근거만, 그 쪽 변화와 같은 힘)를 더하고, `<stock>`에 `big_change`·`etf_change`를 넣는다. 스키마는 이유마다 `side`(big / etf) 칸이 필수다.
- **검사** (`check_reasons(..., etf_until)`): big 이유는 기준일 이전, etf 이유는 ETF 최신일 이전 날짜로 `check_evidence`에 넣는다. 다른 쪽 근거를 고르면 걸린다. 나머지 검사(경로·모호·금리 사건·금지 표현)는 같다.
- **방향** (`direction_warnings(..., etf)`): big 이유는 `change`, etf 이유는 `etf_change`와 같아야 한다. 반대이거나 한쪽 이유가 없으면(그 쪽 근거가 있을 때만) 한 번 다시 쓰게 한다(`retry_message`). 그래도 반대인 이유는 뺀다. 이유가 하나도 안 남으면 rejected다. 한쪽만 남으면 published이고 빈 쪽은 `missing_sides`(model_info.missing_sides)에 남긴다. 화면은 그 쪽에 "이 기간 자료로는 설명할 이유를 찾지 못했어요." 고정 문구를 보여 준다.
- **저장**: 이유마다 `side`, 근거마다 `side`가 붙는다. 한쪽 이유와 예전 저장분은 `side`가 없다(`reasons_from_json`이 None으로 읽음).

**지키는 원칙**: 두 쪽 모두 개념 사전 경로와 방향 검사를 그대로 받는다. ETF 쪽 근거는 기준일 뒤 자료지만, ETF가 실제로 움직인 기간(ETF 최신 스냅샷까지)이라 "나중 일을 보고 이유를 지어낸다"는 걱정은 큰손 쪽에만 해당한다. 기술확정안 "근거 날짜 (탭 2)"에 같은 규칙을 적었다.

## 경기 국면 (2026-11-19 B, #183)

- `generate(..., regime=, etf_regime=)`: 큰손 쪽 이유와 한쪽 이유는 `regime`(분기 말 국면), 양쪽 이유의 ETF 쪽 이유는 `etf_regime`(ETF 최신일 국면)으로 사전 경로 방향을 계산한다(`path_and_direction(..., regime)`, `side_regime`). 국면은 `concepts/regime.py`(삼의 법칙 지표 앞 달 값 ≥ 0.5면 recession)가 정하고 `scripts/run_reasons.py`가 넘긴다.
- 방향 검사(`direction_warnings`)는 그 쪽 국면으로 계산한 방향을 큰손·ETF 변화와 비교한다. 예: 실제 사전에서 국채 금리 ▲ → 성장주 가치평가는 평상시 ▼, 경기 침체 ▲(조건부 연결)다. 그래서 "금리가 내려 성장주 매력이 커졌다"(bond_yield down → ▲)로 늘린 이유는 평상시에는 통과하지만, 침체 국면에서는 bond_yield down → ▼라 큰손 늘림과 반대여서 빠진다(침체 때는 위험 프리미엄이 커져 금리가 내려도 성장주가 눌린다).
- 침체 국면이 있으면 사용자 메시지 끝에 "큰손 기준일 무렵은 경기 침체 국면이에요 (FRED SAHMREALTIME 2024-08 = 0.57) … 이 국면에서 방향이 바뀌는 연결: 국채 금리(bond_yield) ▲ → 성장주 가치평가(growth_valuation) ▲ (평상시 ▼)"를 붙인다(`regime_note`, `flipped_edges`). reasons에는 compose의 `find_concept_path`처럼 국면 반영 방향을 알려 주는 도구가 없어서, 뒤집히는 연결을 직접 알려 준다(안 알려 주면 평상시 예시대로 쓰다가 방향 검사에 걸려 이유가 빠진다, #187 리뷰). 시스템 프롬프트의 금리 예시에는 "평상시 기준"이라고 붙였다. 모두 평상시면 사용자 메시지는 예전과 같다.
- 저장: `model_info.regime = {"big": {name, sahm, observed, source}, "etf": {...}?}`. 국면을 넘기지 않으면 남기지 않는다.
- 2026-11-19 3분기: 분기 말 9/30 → 2026-08 지표 −0.07, ETF 최신일 11/18 → 2026-10 지표 0.00이라 둘 다 평상시, 결과는 예전과 같다.

## 종목 단위 방향 (`stock_direction`, conventions P19에서 C가 정하기로 한 규칙)

`overlap_results`는 (큰손, ETF) 쌍마다 `direction`이 있어서, `stock_reasons`에 넣을 종목 하나의 값으로 줄인다. 같은 분기의 그 종목 줄을 모두 본다.

| 값 | 규칙 | 이유 |
|---|---|---|
| `direction` | 한 쌍이라도 `diff` → `diff`. 아니고 한 쌍이라도 `same` → `same`. 모두 `none` → `none` | 엇갈린 쌍이 하나라도 있으면 "왜 방향이 다를까요?"가 맞는 질문이다 |
| `change` | 큰손마다 한 번씩 `big_chg_pct` 부호를 세어 많은 쪽(up/down). 새로 담음(`holdings_13f.change_type = new`)은 변화율이 NULL(P2)이라 +1, 모두 정리는 -1(P12)로 센다. 같으면 변화율 합의 부호(0이면 up). 큰손 값이 없으면(한쪽만 움직인 none) `etf_trend_chg_pct`(003에서 adj → chg로 이름 바뀜) 합의 부호. 둘 다 없으면 만들지 않는다(ValueError) | 제목의 늘렸을까요/줄였을까요는 큰손 쪽 변화로 정한다(reasons.headline) |

## 저장 모양 (`stock_reasons`, A의 004)

`save(conn, base_date, ticker, direction, change, result, now_view, model_info)` → 저장한 `status`.
- `status`: 이유가 없거나 `errors`가 남으면 `rejected`, 이유는 통과했지만 방향 경고가 있으면 (2026-11-18부터 `pending`은 쓰지 않는다. 방향이 반대인 이유는 generate 가 다시 쓰게 한 뒤 빼고 `model_info.warnings`에 남긴다), 그 밖은 `published`(P19 + 2026-11-16 B·C 합의, 서버는 published만). rejected도 저장하고 `model_info.errors`에 까닭을 남긴다.
- `model_info`: `{"calls": 호출 수, "errors": [...]?, "warnings": [방향 경고]?, "dropped": [뺀 이유의 까닭]?, "missing_sides": [양쪽 이유에서 빈 쪽]?, "regime": {"big": …, "etf": …}?, ...부르는 쪽이 더한 값}`. warnings 는 뺀 이유 기록일 뿐 status 에 영향이 없다.
- 같은 (분기, 종목)을 다시 만들면 덮어쓰고 `updated_at = now()`.

`reasons` (카드 ②, JSON 배열, 1~3개):
```json
[{"title": "AI 투자 확대", "body": "…했을 수 있어요.",
  "start_concept": "ai_investment", "change": "up", "end_concept": "semi_earnings",
  "path": ["ai_investment", "gpu_demand", "semi_earnings"], "direction": "up",
  "evidence": [{"no": 1, "source_id": 10, "published_date": "2026-09-12", "title": "…", "issuer_name": "NVIDIA", "url": "https://…"}]}]
```
양쪽 이유면 이유와 근거에 `"side": "big"` / `"etf"`가 더 붙는다.

`now_view` (카드 ③, `stock_now.StockNow.to_json()`, 없으면 NULL):
```json
{"base_date": "2026-09-30",
 "price": {"from_date": "2026-09-29", "from_close": 100.0, "to_date": "2026-11-14", "to_close": 112.5, "return_pct": 12.5},
 "later_sources": [{"source_id": 55, "published_date": "2026-11-12", "title": "…", "url": "https://…",
                    "numbers": {"매출액 전년동기대비(%)": 62.0, "영업이익 전년동기대비 방향": "증가"}}],
 "linked": [{"concept_id": "gpu_demand", "name": "AI 반도체 수요", "reason_title": "AI 투자 확대"}],
 "text": "기준일 뒤 주가는 12.5% 올랐어요. …", "errors": []}
```
- `price`는 기준일 앞뒤 종가가 없으면 null, `text`는 Haiku 문장이 검사를 못 넘으면 null(사실만 보여 준다).
- 키는 snake_case다. 서버가 web 타입(camelCase)으로 바꿀지 그대로 내릴지는 A와 #101에서 정한다.
