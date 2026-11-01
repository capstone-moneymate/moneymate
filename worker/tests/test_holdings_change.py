from compute.holdings_change import Change, classify_changes


def test_classify_changes_hand_example():
    prev = {"A": 100, "B": 200, "C": 50, "D": 0, "G": 300}   # D 는 직전 분기에 이미 exit(0)
    curr = {"A": 120, "B": 200, "E": 10, "F": 0, "G": 225}   # C 는 사라짐, F 는 0
    got = classify_changes(curr, prev)
    assert got == {
        "A": Change(120, 100, 0.2, "increase"),     # (120-100)/100 = 0.2
        "B": Change(200, 200, 0.0, "unchanged"),    # 수량이 정확히 같음
        "E": Change(10, None, None, "new"),         # P2: 직전이 없으면 NULL
        "G": Change(225, 300, -0.25, "decrease"),   # (225-300)/300 = -0.25
        "C": Change(0, 50, -1.0, "exit"),           # P12: shares=0, chg_pct=-1
    }
    # D(직전 0, 이번 없음), F(직전 없음, 이번 0)는 보유한 적이 없으니 행을 만들지 않는다


def test_prev_zero_counts_as_new():
    # 직전 분기 exit 행(0주)을 다시 산 경우는 new (P2: 직전이 0이면 NULL)
    assert classify_changes({"A": 10}, {"A": 0}) == {"A": Change(10, None, None, "new")}


def test_rounding_to_6_places():
    # (2-3)/3 = -0.333333...
    assert classify_changes({"A": 2}, {"A": 3})["A"].chg_pct == -0.333333
