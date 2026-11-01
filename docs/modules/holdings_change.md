> **초안 (Claude 작성, 2026-10-29).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/compute/holdings_change.py

- **한 줄 설명**: `holdings_13f`의 직전 분기 대비 변화(`prev_shares`, `chg_pct`, `change_type`)를 채우고, 전량 매도 종목의 exit 행을 만든다.
- **입력**: `--period`(분기 말), `--save`. DB의 그 분기와 직전 분기 `holdings_13f` 행.
- **하는 일**: 큰손(filer_key)마다 두 분기의 CUSIP별 수량을 여러 법인 합산으로 만들고 `classify_changes`로 비교한다. chg_pct는 (이번 - 직전) / 직전이고, 직전이 없거나 0이면 NULL이다(P2). change_type은 수량 비교만으로 정한다(P13). 직전에 있다가 사라진 종목은 shares=0, chg_pct=-1, exit 행을 대표 CIK로 만든다(P12).
- **출력**: 이번 분기 행 갱신 + exit 행 추가. 큰손별 종류 개수를 출력한다. `--save`가 없으면 되돌린다.
- **주의할 점**: 이번 분기 행이 없으면(공시 전) 건너뛴다. 직전 분기 행이 없으면 전부 new가 되고 경고를 띄운다. 직전 분기 보유가 실제로 없었는지(빈 13F), 수집을 안 한 건지 확인해야 한다. "늘림" 임계값(+5%)은 여기서 쓰지 않고 overlap.py에서만 쓴다. chg_pct는 소수 6자리로 반올림한다.
- **테스트**: `python -m pytest tests/test_holdings_change.py -q` (손계산: 120/100 → +0.2 increase, 225/300 → -0.25 decrease, 사라짐 → exit -1, 직전 0 → new). 실제 데이터 확인(저장 없이): 에크먼 6/30분 increase 4·decrease 3·new 5·unchanged 2·exit 2(GOOG, GOOGL).
