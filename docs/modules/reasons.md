> **초안 (Claude 작성, 2026-11-15).** 담당자 C가 읽고 고쳐서 확정한다. 5주차 시작본. 6주차: 카드 ③은 stock_now.py(docs/modules/stock_now.md), 저장은 save()(A의 004 `stock_reasons`, conventions P19). 실행: 분기마다 `scripts/run_reasons.py`(docs/modules/run_reasons.md), 카드 ③은 run_daily "탭2 지금은" 단계가 매일 갱신. 근거 검사는 B의 `check_evidence`(#130). 남은 것: A의 `/api/stocks/{ticker}` 응답 연결(#101).

# worker/generate/reasons.py

- **한 줄 설명**: 탭 2 종목 상세 카드 ② "이유 (AI 추정)"를 만든다. 큰손·액티브 ETF가 왜 늘리거나 줄였을지 1~3개 이유를 쓰고, 이유마다 인과 뼈대와 근거 자료(날짜 포함)를 붙인다.
- **입력**: 종목(`ticker`, `name`), A의 `overlap_results.direction`(`same`·`diff`·`none`)과 큰손 쪽 변화(`up`·`down`), 공시 기준일(13F 분기 말), 카드 ① 숫자 문장(코드가 만든 것), 근거 후보. 근거 후보는 `load_evidence`가 `raw_sources`에서 그 종목 자료와 **같은 시장의** 거시 발표(미국 종목은 US500·IXIC 키의 FOMC 등, 국내 종목은 KS11·KQ11 키의 한은 등) 중 기준일 앞 92일 안(기준일 포함)에 나온 것을 최근 순으로 20개까지 번호를 붙여 고른다. 근거마다 `numbers`(거시 decision·금리 전후, DART 증감률 등, 중요한 값 8개, 일정 확인 칸 제외)도 프롬프트에 넘기고 저장할 때는 뺀다. 실행은 `cd worker && python -m generate.reasons NVDA 2026-09-30 same up "드러켄밀러 +24%"`.
- **하는 일**: ① 제목은 방향으로 코드가 정한다(같은 방향 늘림 "왜 다 늘렸을까요?", 줄임 "왜 다 줄였을까요?", 다름 "왜 방향이 다를까요?", 한쪽만 "왜 늘렸을까요?"). ② Sonnet 1회 호출(effort medium, `llm_client`로 비용 기록, module=`reasons`). 개념 id와 근거 번호를 JSON 스키마 enum으로 묶어 사전·입력 밖의 값은 나올 수 없다. ③ 코드 검사: 이유 1~3개, 근거 번호 1개 이상·입력에 있음·같은 번호 두 번 아님·날짜가 기준일 이전(B의 `validators.check_evidence`, #130), 시작≠끝이고 사전에 경로가 있음, 경로마다 방향이 다른 모호한 쌍이 아님(graph.py 규칙, #85 리뷰), 금지 표현(B의 `find_banned`). ④ 걸리면 이유를 돌려주고 1번 더 쓰게 한다. 그래도 걸리면 혼자 검사해서 통과하는 이유만 살리고 뺀 까닭은 `dropped`(model_info.dropped)에 남긴다(사전에 없는 경로 하나 때문에 종목 전체가 rejected 되던 문제, 2026-11-16). ⑤ 방향 경고(`direction_warnings`): 큰손이 한쪽으로 움직인 종목(same·none)에서 이유의 힘이 큰손 변화와 반대면 "큰손 방향과 맞는 경로만 골라" 한 번 다시 쓰게 하고(`MAX_DIRECTION_RETRIES` = 1), 그래도 반대인 이유는 빼서 `warnings`에 남긴다. 하나도 안 남으면 errors("큰손 변화와 방향이 맞는 이유가 없어요") → `rejected`(2026-11-18 B 제안. 11-16~17에는 `pending`으로 두고 사람이 봤다). diff 종목은 보지 않는다. ⑥ 금리 사건 개념(B 결정 2026-11-16): `rate_hold`는 이유의 시작 개념에서 뺀다(스키마 enum, `NOT_START`). `rate_hike`·`rate_cut`은 근거에 실제 그 결정(numbers.decision = hike·cut)이 있고 change가 up일 때만 시작 개념이 된다(`DECISION_EVENTS`, 어기면 다시 쓰게 함). 끝 개념으로는 쓸 수 있다.
- **출력**: `ReasonsResult(headline, reasons, errors, calls, warnings)`. 이유마다 `title`, `body`, `start_concept`, `change`(시작 개념의 변화: 커짐·일어남 up / 줄어듦 down, LLM이 enum으로 고름. 5주차 노션 제안 (1)), `end_concept`, `path`(B의 graph.py로 찾은 가장 짧은 사전 경로), `direction`(시작 개념이 change 했을 때 끝 개념이 받는 힘 up ▲ / down ▼, `graph.effect(g, start, end, change)`로 코드가 계산. 화면 표시용), `evidence`(번호·`raw_sources.id`·날짜·제목·발표 기관·URL). 끝내 통과하지 못하면 `reasons`가 비고 `errors`에 마지막 이유가 남는다. 근거 후보가 없으면 API를 부르지 않는다.
- **주의할 점**: 이유는 추정이다. 근거 번호를 고른 것이 그 자료가 이유를 증명한다는 뜻은 아니다. 숫자는 카드 ①과 근거의 제목·numbers에 있는 것만 쓰게 했지만 문장 속 숫자를 코드가 다시 확인하지는 않는다. 2026-11-16 2분기 20종목 실데이터: 근거로 제목만 넘겼을 때는 FOMC 동결을 "금리 부담이 줄었다"로 지어내고 미국 종목에 한은 결정이 들어갔다 → numbers 전달과 시장 필터 뒤에는 "FOMC가 4월과 6월 모두 3.75%로 동결"처럼 사실대로 쓴다. 이유가 사전 경로 두 가지(rate_hold → growth_valuation, corp_earnings → eps)로 반복되고(근거가 8-K 제목·FOMC뿐이고 8-K는 numbers가 없음), same·none 종목 이유 22개 중 11개는 경로 방향이 큰손 변화와 반대였다. 시작 개념 change를 받은 뒤 다시 생성하면($0.29) 반대가 6개로 줄었다: "순이익이 줄어 줄였다"는 corp_earnings(down) → eps ▼로 맞게 계산된다(6개). 남은 6개는 모두 늘린 종목에 붙은 "금리 동결(up) → 성장주 가치평가 ▼"였다. B 결정으로 rate_hold를 시작 개념에서 뺐더니 2분기(4/29·6/17 모두 동결) 20종목 중 18곳에서 동결을 rate_hike(down)·rate_cut(down)으로 돌려 썼다 → 실제 결정이 있을 때만 쓰게 막은 뒤 다시 생성: 금리 이유 0, 방향 경고 0, 17 published·3 rejected(ARM·TSM 쓸 이유 없음, BE 사전에 없는 경로). 이유가 대부분 "8-K 실적 발표 → 기업 순이익"(16/19) 하나라 얇다. 8-K는 제목만 있어 "공시 내용은 알 수 없지만"이라고 쓴다 → 8-K에 SEC XBRL 분기 실적을 붙였다(collectors/sec_numbers.py). 다시 생성하면 이유가 숫자를 근거로 쓰지만("당기순이익이 전년 동기보다 60.9% 늘었다") LLM이 사전에 없는 revenue → eps·corp_earnings 경로를 골라 11곳이 통째로 rejected → 통과한 이유만 살리게 바꾼 뒤: 12 published·3 pending·5 rejected, 이유 16개 모두 증감률 인용. pending 3곳(MU·AAPL·COHR)은 "호실적 뒤 차익 실현"(순이익 ▲인데 줄임)이었고, B와 검토해 사전 밖 설명(투자자 행동, 1차 자료로 방향 확인 불가)이라 rejected로 정했다(2026-11-18). rejected는 revenue → corp_earnings·eps 경로가 사전에 없음 3곳(B에게 요청), 해외 발행사라 8-K가 없음 2곳(ARM·TSM). 기사 본문은 넘기지 않고 제목만 쓴다(CLAUDE.md 9). 근거 날짜 검사는 #85에서 약속한 대로 B의 근거 날짜 검증기(`check_evidence`, #130)로 바꿨다(2026-11-17). 오류 문장은 예전과 같고, 같은 근거 번호를 두 번 고르면 새로 걸린다. 방향 경고는 끝 개념이 "커지면 늘릴 이유"라고 가정한다. 비용·금리처럼 커지면 줄일 이유인 끝 개념은 경고가 거꾸로 나올 수 있어서 거부하지 않는다(사전에 그 정보가 없음). 금리 뉴스와 AI 테마는 #67 이후 사전에서 이어지지 않아 그런 이유는 경로 검사에서 걸린다.
- **테스트**: `cd worker && python -m pytest tests/test_reasons.py -q` (가짜 응답: 방향 반대면 한 번 다시 쓰기·그래도 반대인 이유만 빼기·하나도 없으면 rejected·엇갈린 종목은 다시 쓰지 않음, save 에 pending 없음, 방향별 제목 4가지, 정상 이유와 코드가 찾은 경로, 스키마 enum, 프롬프트 JSON 묶기, 불량 8가지(모호한 쌍 포함), 누르는 힘 경로의 방향, 기준일 뒤 근거, 금지 표현, 수정 1회 후 통과, 수정 상한, 근거 없으면 호출 안 함, 잘린 응답, change 가 down 이면 방향이 뒤집혀 줄임과 맞음, change 칸 없는 예전 응답은 up·경고, diff 는 경고 안 함, rate_hold 는 시작 enum 에서 빠지고 끝 enum 에는 남음, rate_hike 는 근거에 hike 결정이 있고 change up 일 때만, 고쳐 쓰기 뒤에도 걸리면 통과한 이유만 살리고 dropped 에 남김). 저장 status 는 `tests/test_stock_now.py`(경고 있으면 pending). 저장·종목 방향은 `tests/test_stock_now.py`(published·rejected upsert 인자, 방향 규칙 손계산). 2026-11-16 로컬 DB에 004 적용 뒤 시험 줄을 published → rejected로 두 번 저장해 한 줄 덮어쓰기 확인, 시험 줄은 지움. 실데이터(2분기 20종목) 확인은 docs/modules/run_reasons.md.

## 종목 단위 방향 (`stock_direction`, conventions P19에서 C가 정하기로 한 규칙)

`overlap_results`는 (큰손, ETF) 쌍마다 `direction`이 있어서, `stock_reasons`에 넣을 종목 하나의 값으로 줄인다. 같은 분기의 그 종목 줄을 모두 본다.

| 값 | 규칙 | 이유 |
|---|---|---|
| `direction` | 한 쌍이라도 `diff` → `diff`. 아니고 한 쌍이라도 `same` → `same`. 모두 `none` → `none` | 엇갈린 쌍이 하나라도 있으면 "왜 방향이 다를까요?"가 맞는 질문이다 |
| `change` | 큰손마다 한 번씩 `big_chg_pct` 부호를 세어 많은 쪽(up/down). 새로 담음(`holdings_13f.change_type = new`)은 변화율이 NULL(P2)이라 +1, 모두 정리는 -1(P12)로 센다. 같으면 변화율 합의 부호(0이면 up). 큰손 값이 없으면(한쪽만 움직인 none) `etf_trend_chg_pct`(003에서 adj → chg로 이름 바뀜) 합의 부호. 둘 다 없으면 만들지 않는다(ValueError) | 제목의 늘렸을까요/줄였을까요는 큰손 쪽 변화로 정한다(reasons.headline) |

## 저장 모양 (`stock_reasons`, A의 004)

`save(conn, base_date, ticker, direction, change, result, now_view, model_info)` → 저장한 `status`.
- `status`: 이유가 없거나 `errors`가 남으면 `rejected`, 이유는 통과했지만 방향 경고가 있으면 (2026-11-18부터 `pending`은 쓰지 않는다. 방향이 반대인 이유는 generate 가 다시 쓰게 한 뒤 빼고 `model_info.warnings`에 남긴다), 그 밖은 `published`(P19 + 2026-11-16 B·C 합의, 서버는 published만). rejected도 저장하고 `model_info.errors`에 까닭을 남긴다.
- `model_info`: `{"calls": 호출 수, "errors": [...]?, "warnings": [방향 경고]?, "dropped": [뺀 이유의 까닭]?, ...부르는 쪽이 더한 값}`. warnings 는 뺀 이유 기록일 뿐 status 에 영향이 없다.
- 같은 (분기, 종목)을 다시 만들면 덮어쓰고 `updated_at = now()`.

`reasons` (카드 ②, JSON 배열, 1~3개):
```json
[{"title": "AI 투자 확대", "body": "…했을 수 있어요.",
  "start_concept": "ai_investment", "change": "up", "end_concept": "semi_earnings",
  "path": ["ai_investment", "gpu_demand", "semi_earnings"], "direction": "up",
  "evidence": [{"no": 1, "source_id": 10, "published_date": "2026-09-12", "title": "…", "issuer_name": "NVIDIA", "url": "https://…"}]}]
```

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
