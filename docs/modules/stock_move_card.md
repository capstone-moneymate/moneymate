> 초안 (Claude 작성, 2026-11-21). 담당자 C가 읽고 고쳐서 확정한다.

# worker/generate/stock_move_card.py

- **한 줄 설명:** 탭 1 홈 종목 차트가 매일 하나는 나오게 하는 규칙과, 시장 반응 1위 종목의 주가·거래량 움직임 카드 자료.
- **규칙:** 하루 카드 중 최소 1장은 차트를 그릴 수 있는 종목 카드(`market` 이 KR·US 이고 ticker 가 있는 자료). 종목 카드가 있으면 그중 선별 점수 1위가 차트(`chart_candidate`, 동점은 `rank_key`). 거시 뉴스만 고른 날은 점수 최하위 카드를 빼고 반응 1위 종목 카드를 넣는다(`with_stock_card`, 3장 미만이면 빼지 않고 더함).
- **입력:** 기준일, 그날 국내 전 종목 선별 점수표(`cross_section_scores`), 이미 고른 종목(빼기).
- **하는 일:** 점수 1점 이상 국내 보통주 중 그날 시가총액 1조 원 이상(`MIN_MARKET_CAP`, pykrx)에서 점수 → 거래량 점수 → 수익률 점수 → 평소 대비 거래량 순 1위(`top_reactor`). 하한을 넘는 종목이 없거나 시가총액을 못 받으면 하한 없이 고른다(차트는 항상 하나). 종가·등락률·직전 20거래일 평균 거래량·배수를 코드가 계산해 raw_sources 한 줄(`source_type 'price'`, `category 'stock_move'`)로 저장, 유형 1·시작 개념 없음으로 compose. 같은 날 그 종목 자료는 card_sources 에 `is_main = false` 로 묶는다.
- **출력:** 출제 후보(Candidate, `is_price_card = True`). 출제 뒤 `cards.model_info.select = {score, vol_score, ret_score, stock, chart}` (스키마 변경 없음). 서버는 `select.chart = true` 인 카드를 홈 종목 차트로 쓴다(서버 미구현).
- **주의할 점:** 반응 1위는 국내만 본다(미국은 전 종목 점수표가 없음). 같은 날 자료는 원인으로 단정하지 않는다(compose.md "오늘의 종목 움직임 카드"). 그날 국내 가격이 없으면 None.
- **정한 것:** 소형주 급등락이 홈 차트가 되지 않게 시가총액 하한을 둔다 (C, 2026-11-21). 11/18 은 하한 전 오리콤(-16.88%) → 하한 뒤 JYP Ent.(+8.72%, 거래량 3.7배).
- **열린 질문:** 하한 값 1조 원이 적당한지.
- **테스트 순서:** `tests/test_stock_move_card.py` (규칙·손계산 숫자·run_daily 연결) → `python -m generate.stock_move_card 2026-11-18 --no-llm` 으로 실제 DB에서 고른 종목 확인.
