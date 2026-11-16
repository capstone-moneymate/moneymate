> **초안 (Claude 작성, 2026-11-15).** 담당자 C가 읽고 고쳐서 확정한다. 5주차 시작본. 6주차: 카드 ③은 stock_now.py(docs/modules/stock_now.md), 저장은 save()(A의 004 `stock_reasons`, conventions P19). 남은 것: B의 근거 날짜 검증기, run_daily(13F 분기 갱신) 연결, A의 `/api/stocks/{ticker}` 응답 연결(#101).

# worker/generate/reasons.py

- **한 줄 설명**: 탭 2 종목 상세 카드 ② "이유 (AI 추정)"를 만든다. 큰손·액티브 ETF가 왜 늘리거나 줄였을지 1~3개 이유를 쓰고, 이유마다 인과 뼈대와 근거 자료(날짜 포함)를 붙인다.
- **입력**: 종목(`ticker`, `name`), A의 `overlap_results.direction`(`same`·`diff`·`none`)과 큰손 쪽 변화(`up`·`down`), 공시 기준일(13F 분기 말), 카드 ① 숫자 문장(코드가 만든 것), 근거 후보. 근거 후보는 `load_evidence`가 `raw_sources`에서 그 종목 자료와 거시 발표 중 기준일 앞 92일 안(기준일 포함)에 나온 것을 최근 순으로 20개까지 번호를 붙여 고른다. 실행은 `cd worker && python -m generate.reasons NVDA 2026-09-30 same up "드러켄밀러 +24%"`.
- **하는 일**: ① 제목은 방향으로 코드가 정한다(같은 방향 늘림 "왜 다 늘렸을까요?", 줄임 "왜 다 줄였을까요?", 다름 "왜 방향이 다를까요?", 한쪽만 "왜 늘렸을까요?"). ② Sonnet 1회 호출(effort medium, `llm_client`로 비용 기록, module=`reasons`). 개념 id와 근거 번호를 JSON 스키마 enum으로 묶어 사전·입력 밖의 값은 나올 수 없다. ③ 코드 검사: 이유 1~3개, 근거 번호 1개 이상·입력에 있음·날짜가 기준일 이전, 시작≠끝이고 사전에 경로가 있음, 경로마다 방향이 다른 모호한 쌍이 아님(graph.py 규칙, #85 리뷰), 금지 표현(B의 `find_banned`). ④ 걸리면 이유를 돌려주고 1번 더 쓰게 한다.
- **출력**: `ReasonsResult(headline, reasons, errors, calls)`. 이유마다 `title`, `body`, `start_concept`, `end_concept`, `path`(B의 graph.py로 찾은 가장 짧은 사전 경로), `direction`(시작 개념이 커질 때 끝 개념이 받는 힘 up ▲ / down ▼, 사전 경로로 코드가 계산. 화면 표시용), `evidence`(번호·`raw_sources.id`·날짜·제목·발표 기관·URL). 끝내 통과하지 못하면 `reasons`가 비고 `errors`에 마지막 이유가 남는다. 근거 후보가 없으면 API를 부르지 않는다.
- **주의할 점**: 이유는 추정이다. 근거 번호를 고른 것이 그 자료가 이유를 증명한다는 뜻은 아니다. 숫자는 카드 ①과 자료 제목에 있는 것만 쓰게 했지만 문장 속 숫자를 코드가 다시 확인하지는 않는다(6주차 검토). 기사 본문은 넘기지 않고 제목만 쓴다(CLAUDE.md 9). 근거 날짜 검사는 지금 이 파일에 있고, B가 validators에 근거 날짜 검증기를 만들면 그것으로 바꾼다(B가 만들기로 함, #85). `direction`이 큰손의 늘림·줄임과 맞는지는 아직 검사하지 않는다(시작 개념이 줄어든 경우도 있어 단순 비교가 어려움). 금리 뉴스와 AI 테마는 #67 이후 사전에서 이어지지 않아 그런 이유는 경로 검사에서 걸린다.
- **테스트**: `cd worker && python -m pytest tests/test_reasons.py -q` (가짜 응답: 방향별 제목 4가지, 정상 이유와 코드가 찾은 경로, 스키마 enum, 프롬프트 JSON 묶기, 불량 8가지(모호한 쌍 포함), 누르는 힘 경로의 방향, 기준일 뒤 근거, 금지 표현, 수정 1회 후 통과, 수정 상한, 근거 없으면 호출 안 함, 잘린 응답). 저장·종목 방향은 `tests/test_stock_now.py`(published·rejected upsert 인자, 방향 규칙 손계산). 2026-11-16 로컬 DB에 004 적용 뒤 시험 줄을 published → rejected로 두 번 저장해 한 줄 덮어쓰기 확인, 시험 줄은 지움. **실제 API·DB로는 아직 확인하지 못했다**(raw_sources에 NVDA 자료와 3분기 13F 겹침 결과가 있어야 함).

## 종목 단위 방향 (`stock_direction`, conventions P19에서 C가 정하기로 한 규칙)

`overlap_results`는 (큰손, ETF) 쌍마다 `direction`이 있어서, `stock_reasons`에 넣을 종목 하나의 값으로 줄인다. 같은 분기의 그 종목 줄을 모두 본다.

| 값 | 규칙 | 이유 |
|---|---|---|
| `direction` | 한 쌍이라도 `diff` → `diff`. 아니고 한 쌍이라도 `same` → `same`. 모두 `none` → `none` | 엇갈린 쌍이 하나라도 있으면 "왜 방향이 다를까요?"가 맞는 질문이다 |
| `change` | 큰손마다 한 번씩 `big_chg_pct` 부호를 세어 많은 쪽(up/down). 같으면 변화율 합의 부호(0이면 up). 큰손 값이 없으면(한쪽만 움직인 none) `etf_trend_adj_pct` 합의 부호. 둘 다 없으면 만들지 않는다(ValueError) | 제목의 늘렸을까요/줄였을까요는 큰손 쪽 변화로 정한다(reasons.headline) |

## 저장 모양 (`stock_reasons`, A의 004)

`save(conn, base_date, ticker, direction, change, result, now_view, model_info)` → 저장한 `status`.
- `status`: 이유가 있고 `errors`가 비면 `published`, 아니면 `rejected`(P19, 서버는 published만). rejected도 저장하고 `model_info.errors`에 까닭을 남긴다.
- `model_info`: `{"calls": 호출 수, "errors": [...]?, ...부르는 쪽이 더한 값}`.
- 같은 (분기, 종목)을 다시 만들면 덮어쓰고 `updated_at = now()`.

`reasons` (카드 ②, JSON 배열, 1~3개):
```json
[{"title": "AI 투자 확대", "body": "…했을 수 있어요.",
  "start_concept": "ai_investment", "end_concept": "semi_earnings",
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
