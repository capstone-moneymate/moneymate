> **초안 (Claude 작성, 2026-10-29).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/compute/overlap.py

- **한 줄 설명**: 큰손 13F 변화와 액티브 ETF 추세의 방향을 같은 시점 기준으로 비교해 `overlap_results`에 same / diff / none을 저장한다.
- **입력**: `--period`(13F 분기 말), `--save`. DB의 그 분기 `holdings_13f`(holdings_change를 먼저 돌려야 함)와 그 분기 말 이후의 `holdings_etf` 스냅샷.
- **하는 일**: 13F 방향은 new → 늘림, exit → 줄임, 그 외는 chg_pct가 ±`INCREASE_THRESHOLD`(5%) 이상일 때만 늘림·줄임이다(P13). ETF는 분기 말 이후 첫 스냅샷(기준)과 최신 스냅샷의 1CU 수량을 비교한다. 기준일에 없다가 생기면 늘림, 있다가 없어지면 줄임, 둘 다 있으면 ±`ETF_TREND_THRESHOLD`(임시 5%) 기준이다. 두 방향이 같으면 same, 반대면 diff, 한쪽이 없으면 none이다(P3). 13F와 ETF는 CUSIP 2~7번째 글자 = `raw_code`로 맞춘다.
- **출력**: (계산일, 티커, 큰손, ETF)마다 한 줄. ETF가 기준일이나 최신에 그 종목을 가진 쌍만 만든다. 같은 날 다시 돌리면 덮어쓴다. `co_increased()`는 탭 2의 "2명 이상 함께 늘린 종목"용 함수다.
- **주의할 점**: ETF 변화율은 B의 `trend_chg_pct`를 읽지 않고 여기서 같은 식(P2)으로 직접 계산한다. B의 trend_base_date(9/30)와 13F 분기 말(지금 개발용 6/30)이 달라도 P7을 지키기 위해서다. B의 etf_trend가 완성되면 기준일이 같을 때 그 값을 쓸지 B와 정한다. 줄임 임계값은 늘림과 같은 크기로 두었다(결정 필요). 티커가 없는 13F 행은 뺀다. 6자리가 다른 회사와 겹칠 수 있어 결과는 종목명으로 한 번 확인한다.
- **테스트**: `python -m pytest tests/test_overlap.py -q` (손계산: KoAct NVIDIA 99.88 → 104.874 = +5% 늘림, TIME NVIDIA 239 → 200 = -16.318% 줄임 → 큰손 +10%와 diff, 신규 매수 vs ETF 전량 정리 → diff). DB 실행은 B의 ETF 수집과 003 적용 후에 확인한다.
