"""차트 종목 카드 규칙 테스트 (DB·네트워크 없음). 손계산 예시가 정답이다."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

import run_daily as rd
from compute.source_select import Candidate
from generate.stock_move_card import (average_volume, build_source, chart_candidate, is_stock_source,
                                      select_info, top_reactor, with_stock_card)

KST = ZoneInfo("Asia/Seoul")


def cand(key, vol, ret, ticker=None, market=None, price=False):
    src = {"title": key, "ticker": ticker, "market": market}
    return Candidate(key, key, datetime(2026, 11, 17, 9, tzinfo=KST), vol_score=vol, ret_score=ret,
                     start_concept="x", is_price_card=price, extra={"source": src})


def test_is_stock_source_only_kr_us_with_ticker():
    assert is_stock_source({"ticker": "005930", "market": "KR"})
    assert is_stock_source({"ticker": "NVDA", "market": "US"})
    assert not is_stock_source({"ticker": "KS11", "market": "INDEX"})  # 지수
    assert not is_stock_source({"ticker": None, "market": None})       # 거시 발표
    assert not is_stock_source(None)


def test_chart_candidate_is_top_score_stock():
    rate = cand("금리", 3, 3)                       # 점수 6이지만 종목이 아니다
    hynix = cand("하이닉스", 2, 2, "000660", "KR")  # 4
    nvda = cand("엔비디아", 3, 2, "NVDA", "US")     # 5 → 1위
    assert chart_candidate([rate, hynix, nvda]) is nvda
    assert chart_candidate([rate]) is None


def test_chart_candidate_tie_prefers_volume():
    a = cand("A", 1, 3, "000001", "KR")  # 4, 거래량 1
    b = cand("B", 3, 1, "000002", "KR")  # 4, 거래량 3 → 이긴다 (rank_key)
    assert chart_candidate([a, b]) is b


def test_with_stock_card_keeps_picked_when_stock_exists():
    picked = [cand("금리", 3, 3), cand("하이닉스", 1, 1, "000660", "KR")]
    filler = cand("반응1위", 3, 3, "123450", "KR", price=True)
    assert with_stock_card(picked, filler, 3) == picked


def test_with_stock_card_drops_lowest_macro_when_full():
    a, b, c = cand("금리", 3, 3), cand("고용", 2, 1), cand("물가", 1, 1)  # 6, 3, 2 → 물가가 최하위
    filler = cand("반응1위", 3, 2, "123450", "KR", price=True)
    assert with_stock_card([a, b, c], filler, 3) == [a, b, filler]


def test_with_stock_card_adds_when_room_or_empty():
    a = cand("금리", 3, 3)
    filler = cand("반응1위", 3, 2, "123450", "KR", price=True)
    assert with_stock_card([a], filler, 3) == [a, filler]
    assert with_stock_card([], filler, 3) == [filler]  # 자료가 하나도 없는 날에도 차트는 나온다
    assert with_stock_card([a], None, 3) == [a]        # 고를 종목이 없으면 그대로


def scores(rows):
    df = pd.DataFrame(rows, columns=["ticker", "vol_score", "ret_score", "abn_volume"])
    df["score"] = df["vol_score"] + df["ret_score"]
    return df.set_index("ticker")


def test_top_reactor_highest_score_common_stock():
    s = scores([
        ("005930", 1, 1, 0.5),
        ("000660", 3, 2, 2.0),   # 5 → 1위
        ("000665", 3, 3, 9.0),   # 우선주(끝자리 5)는 지수·차트에서 뺀다
        ("035720", 2, 2, 1.0),
    ])
    assert top_reactor(s) == "000660"
    assert top_reactor(s, exclude={"000660"}) == "035720"  # 이미 고른 종목은 뺀다


def test_top_reactor_ties_and_empty():
    s = scores([("000100", 2, 2, 1.0), ("000200", 3, 1, 0.1), ("000300", 3, 1, 0.9)])
    assert top_reactor(s) == "000300"  # 4점 동점 → 거래량 점수 3 → abn_volume 큰 쪽
    assert top_reactor(scores([("000100", 0, 0, 1.0)])) is None  # 1점 이상만
    assert top_reactor(pd.DataFrame()) is None  # 그날 국내 가격이 없으면 빈 표


def test_top_reactor_market_cap_floor():
    s = scores([
        ("010470", 2, 2, 4.9),   # 4점 1위지만 시가총액 300억 → 하한 아래
        ("000660", 2, 1, 2.0),   # 3점, 시가총액 150조 → 고른다
        ("035720", 1, 1, 1.0),
    ])
    caps = {"010470": 3e10, "000660": 1.5e14, "035720": 2e13}
    assert top_reactor(s) == "010470"                     # 시가총액을 모르면 점수 1위
    assert top_reactor(s, caps=caps) == "000660"          # 1조 원 이상 중 점수 1위
    assert top_reactor(s, {"000660"}, caps) == "035720"   # 빼기와 함께 쓴다
    small = {"010470": 3e10, "000660": 5e11, "035720": 9e11}
    assert top_reactor(s, caps=small) == "010470"         # 하한을 넘는 종목이 없으면 하한 없이


def test_average_volume_skips_missing_and_zero():
    assert average_volume([100, None, 300]) == 200
    assert average_volume([None, None]) is None
    assert average_volume([0, 0]) is None
    assert average_volume(list(range(1, 31)), n=20) == sum(range(11, 31)) / 20  # 직전 20일만


def test_build_source_numbers_by_hand():
    same = [{"title": "단일판매·공급계약 체결"}]
    src = build_source("000660", "SK하이닉스", date(2026, 11, 17), 210000, 200000, 5_000_000, 1_000_000,
                       3, 2, same)
    n = src["numbers"]
    assert n["등락률(%)"] == 5.0 and n["방향"] == "상승"   # 210000 / 200000 - 1 = 5%
    assert n["평소 대비 거래량(배)"] == 5.0               # 5,000,000 / 1,000,000
    assert n["같은 날 자료 1"] == "단일판매·공급계약 체결"
    assert src["source_type"] == "price" and src["category"] == "stock_move"
    assert src["ticker"] == "000660" and src["market"] == "KR"   # 차트를 그릴 수 있는 종목 자료
    assert src["source_key"] == "000660_stock_move_2026-11-17"
    assert src["title"] == "SK하이닉스 5.00% 상승 · 거래량 평소의 5.0배"


def test_build_source_without_same_day_says_none():
    src = build_source("000660", "SK하이닉스", date(2026, 11, 17), 190000, 200000, None, None, 0, 2, [])
    assert src["numbers"]["같은 날 자료"] == "이 종목에 대한 공시 없음"
    assert "평소 대비 거래량(배)" not in src["numbers"]
    assert src["numbers"]["방향"] == "하락"


def test_select_info_marks_only_chart_card():
    rate = cand("금리", 3, 3)
    nvda = cand("엔비디아", 3, 2, "NVDA", "US")
    failed = cand("하이닉스", 2, 2, "000660", "KR")  # 출제 실패 → card_id 없음 → 빠진다
    rate.extra["card_id"], nvda.extra["card_id"] = 11, 12
    info = select_info([rate, nvda, failed], nvda)
    assert info == {
        11: {"score": 6, "vol_score": 3, "ret_score": 3, "stock": False, "chart": False},
        12: {"score": 5, "vol_score": 3, "ret_score": 2, "stock": True, "chart": True},
    }


# --- run_daily 연결 ---

def pipeline(monkeypatch, tmp_path, cands, filler):
    calls = []
    monkeypatch.setattr(rd, "LOG_PATH", tmp_path / "run_daily.jsonl")
    monkeypatch.setattr(rd, "score_sources", lambda d: cands)
    monkeypatch.setattr(rd, "classify_candidates", lambda c: c)
    monkeypatch.setattr(rd, "stock_move_candidate", lambda t, p: calls.append("stock_move") or filler)
    monkeypatch.setattr(rd, "compose_selected",
                        lambda p, d: calls.append(("compose", [c.extra["source"]["title"] for c in p])) or [1])
    monkeypatch.setattr(rd, "ensure_chart_card", lambda p, t, d: calls.append("chart") or [])
    monkeypatch.setattr(rd, "debate_cards", lambda ids: "ok")
    monkeypatch.setattr(rd, "refresh_now_views", lambda d: "ok")
    return calls


def test_run_macro_only_day_swaps_lowest_for_reactor(monkeypatch, tmp_path):
    macro = [cand("금리", 3, 3), cand("고용", 2, 1), cand("물가", 1, 1)]
    filler = cand("반응1위", 3, 2, "123450", "KR", price=True)
    calls = pipeline(monkeypatch, tmp_path, macro, filler)
    rd.run(date(2026, 11, 17), date(2026, 11, 18), collect=False)
    assert calls[:2] == ["stock_move", ("compose", ["금리", "고용", "반응1위"])]
    assert calls[2] == "chart"


def test_run_with_stock_card_does_not_look_for_reactor(monkeypatch, tmp_path):
    picked = [cand("금리", 3, 3), cand("하이닉스", 1, 1, "000660", "KR")]
    calls = pipeline(monkeypatch, tmp_path, picked, None)
    rd.run(date(2026, 11, 17), date(2026, 11, 18), collect=False)
    assert "stock_move" not in calls
    assert ("compose", ["금리", "하이닉스"]) in calls


def test_run_without_any_source_still_makes_chart_card(monkeypatch, tmp_path):
    filler = cand("반응1위", 3, 2, "123450", "KR", price=True)
    calls = pipeline(monkeypatch, tmp_path, [], filler)
    rd.run(date(2026, 11, 17), date(2026, 11, 18), collect=False)
    assert ("compose", ["반응1위"]) in calls


def test_ensure_chart_card_retries_when_stock_compose_failed(monkeypatch):
    import generate.stock_move_card as smc

    rate = cand("금리", 3, 3)
    rate.extra["card_id"] = 11
    hynix = cand("하이닉스", 2, 2, "000660", "KR")  # 출제 실패 (card_id 없음)
    filler = cand("반응1위", 3, 2, "123450", "KR", price=True)
    seen, saved = [], []
    monkeypatch.setattr(rd, "stock_move_candidate", lambda t, p: seen.append([c.event_key for c in p]) or filler)

    def fake_compose(p, d):
        p[0].extra["card_id"] = 13
        return [13]

    monkeypatch.setattr(rd, "compose_selected", fake_compose)
    monkeypatch.setattr(smc, "save_select_info", lambda info: saved.append(info))
    assert rd.ensure_chart_card([rate, hynix], date(2026, 11, 17), date(2026, 11, 18)) == [13]
    assert seen == [["금리", "하이닉스"]]  # 실패한 하이닉스는 빼고 다음 종목을 고른다
    assert saved[0][13]["chart"] is True and saved[0][11]["chart"] is False


def test_ensure_chart_card_marks_existing_stock_card(monkeypatch):
    import generate.stock_move_card as smc

    nvda = cand("엔비디아", 3, 2, "NVDA", "US")
    nvda.extra["card_id"] = 12
    saved = []
    monkeypatch.setattr(rd, "stock_move_candidate", lambda t, p: (_ for _ in ()).throw(AssertionError("안 불려야 함")))
    monkeypatch.setattr(smc, "save_select_info", lambda info: saved.append(info))
    assert rd.ensure_chart_card([nvda], date(2026, 11, 17), date(2026, 11, 18)) == []
    assert saved == [{12: {"score": 5, "vol_score": 3, "ret_score": 2, "stock": True, "chart": True}}]
