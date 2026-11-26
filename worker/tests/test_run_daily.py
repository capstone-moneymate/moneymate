"""run_daily.py 테스트. DB·네트워크·Claude 는 부르지 않는다 (단계 함수를 가짜로 바꾼다)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

import run_daily as rd
from compute.source_select import Candidate

KST = ZoneInfo("Asia/Seoul")


# --- 단계 실행: 실패해도 계속, 마지막에 실패 표시 ---

def test_run_step_records_ok_and_exit_code():
    report = rd.DailyReport("2026-11-13", "now")
    assert rd.run_step(report, "성공", lambda: "3건") == "3건"
    rd.run_step(report, "ETF", lambda: 1)  # etf_holdings.main 이 실패하면 1 (B 요청 4)
    rd.run_step(report, "0 은 성공", lambda: 0)
    assert [(s.name, s.ok) for s in report.steps] == [("성공", True), ("ETF", False), ("0 은 성공", True)]
    assert report.steps[1].detail == "종료 코드 1" and not report.ok


def test_run_step_catches_exception_and_continues():
    report = rd.DailyReport("2026-11-13", "now")

    def boom():
        raise ConnectionError("KRX 응답 없음")

    assert rd.run_step(report, "가격", boom) is None
    assert report.steps[0].ok is False and "ConnectionError: KRX 응답 없음" in report.steps[0].detail


def fake_pipeline(monkeypatch, tmp_path, *, etf_code=0, picked_titles=("A", "B")):
    calls = []
    monkeypatch.setattr(rd, "LOG_PATH", tmp_path / "run_daily.jsonl")
    monkeypatch.setattr(rd, "collect_prices", lambda d: calls.append("prices") or "ok")
    monkeypatch.setattr(rd, "collect_sources", lambda d: calls.append("sources") or 0)
    monkeypatch.setattr(rd, "collect_etf", lambda d: calls.append(("etf", d)) or etf_code)
    monkeypatch.setattr(rd, "compute_etf_trend", lambda d: calls.append("trend") or 0)
    cands = [Candidate(str(i), t, datetime(2026, 11, 13, tzinfo=KST), vol_score=2, start_concept="rate_hold",
                       extra={"source": {"title": t}}) for i, t in enumerate(picked_titles)]
    monkeypatch.setattr(rd, "score_sources", lambda d: calls.append("score") or cands)
    monkeypatch.setattr(rd, "classify_candidates", lambda c: calls.append("classify") or c)
    monkeypatch.setattr(rd, "compose_selected", lambda p, d: calls.append(("compose", len(p), d)) or [7, 8])
    monkeypatch.setattr(rd, "refresh_now_views", lambda d: calls.append(("now", d)) or "갱신 0/0종목")
    monkeypatch.setattr(rd, "debate_cards", lambda ids: calls.append(("debate", list(ids))) or "published 2/2")
    # 차트 종목 카드 단계가 실제 DB 를 부르지 않게 (이 가짜 자료에는 종목이 없다)
    monkeypatch.setattr(rd, "stock_move_candidate", lambda t, p: calls.append("stock_move") or None)
    monkeypatch.setattr(rd, "ensure_chart_card", lambda p, t, d: [])
    return calls


def test_debate_runs_on_composed_cards(monkeypatch, tmp_path):
    calls = fake_pipeline(monkeypatch, tmp_path)
    report = rd.run(date(2026, 11, 13), date(2026, 11, 14), collect=False)
    # 출제한 카드 id 그대로 토론을 만든다 (출제 다음 단계)
    # 그다음 탭2 지금은 갱신이 이어진다
    assert calls[-3:] == [("compose", 2, date(2026, 11, 14)), ("debate", [7, 8]), ("now", date(2026, 11, 14))]
    debate = next(s for s in report.steps if s.name == "토론")
    assert debate.detail == "published 2/2"


def test_no_debate_without_cards(monkeypatch, tmp_path):
    calls = fake_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(rd, "compose_selected", lambda p, d: [])
    rd.run(date(2026, 11, 13), date(2026, 11, 14), collect=False)
    assert not any(isinstance(c, tuple) and c[0] == "debate" for c in calls)


def test_run_continues_after_etf_failure_and_logs(monkeypatch, tmp_path):
    calls = fake_pipeline(monkeypatch, tmp_path, etf_code=1)
    report = rd.run(date(2026, 11, 13), date(2026, 11, 14))
    # ETF 가 실패해도 다음 단계로. ETF 도 기준일을 받는다 (#87 리뷰)
    assert calls[:5] == ["prices", "sources", ("etf", date(2026, 11, 13)), "trend", "score"]
    assert ("compose", 2, date(2026, 11, 14)) in calls and report.card_ids == [7, 8]
    assert not report.ok  # 하지만 하루 결과는 실패로 남는다 → 종료 코드 1
    log = (tmp_path / "run_daily.jsonl").read_text(encoding="utf-8")
    assert '"ok": false' in log and '"target": "2026-11-13"' in log


def test_no_llm_stops_before_classify(monkeypatch, tmp_path):
    calls = fake_pipeline(monkeypatch, tmp_path)
    report = rd.run(date(2026, 11, 13), date(2026, 11, 14), collect=False, llm=False)
    # --no-llm 이면 카드 ③ 갱신도 건너뛴다 (문장 없는 now_view 로 덮어쓰지 않게)
    assert calls == ["score"] and report.ok and report.card_ids == []


def test_now_refresh_runs_after_compose_with_card_date(monkeypatch, tmp_path):
    calls = fake_pipeline(monkeypatch, tmp_path)
    report = rd.run(date(2026, 11, 13), date(2026, 11, 14), collect=False)
    assert calls[-1] == ("now", date(2026, 11, 14))
    step = next(s for s in report.steps if s.name == "탭2 지금은")
    assert step.ok and step.detail == "갱신 0/0종목"  # 문자열 결과라 종료 코드로 오해하지 않는다


def test_refresh_now_views_updates_each_stock_and_reports_failures(monkeypatch):
    from generate import reasons, stock_now

    import collectors.prices as prices
    import db

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def commit(self):
            pass

    base = date(2026, 9, 30)
    raw = [{"title": "t", "body": "b", "start_concept": "gpu_demand", "end_concept": "semi_earnings",
            "path": ["gpu_demand", "semi_earnings"], "direction": "up",
            "evidence": [{"no": 1, "source_id": 10, "published_date": "2026-09-12", "title": "x",
                          "issuer_name": "N", "url": "u"}]}]
    monkeypatch.setattr(db, "get_conn", lambda: Conn())
    monkeypatch.setattr(rd, "load_published_reasons", lambda conn: [(base, "NVDA", raw), (base, "BAD", raw)])
    fetched, saved = [], []
    monkeypatch.setattr(prices, "fetch_us", lambda t, s, e: fetched.append((t, s, e)) or pd.DataFrame())
    monkeypatch.setattr(prices, "save_prices", lambda conn, df: 0)

    def fake_generate(stock, period, rs_, today):
        if stock["ticker"] == "BAD":
            raise ValueError("가격 없음")
        assert rs_[0].evidence[0].source_id == 10 and today == date(2026, 11, 14)  # JSON → Reason 복원
        return stock_now.StockNow(period.isoformat(), text="지금은")

    monkeypatch.setattr(stock_now, "generate", fake_generate)
    monkeypatch.setattr(reasons, "save_now_view", lambda conn, p, t, v: saved.append((t, v["text"])) or 1)

    with pytest.raises(RuntimeError) as e:
        rd.refresh_now_views(date(2026, 11, 14))
    # 기준일 10일 전부터 가격을 받고, 실패한 종목이 있어도 나머지는 저장한다
    assert fetched[0] == ("NVDA", date(2026, 9, 20), date(2026, 11, 14))
    assert saved == [("NVDA", "지금은")]
    assert "갱신 1/2종목" in str(e.value) and "BAD: ValueError" in str(e.value)


def test_collect_etf_backfills_from_target(monkeypatch):
    # --date 로 다시 돌리거나 전날 수집이 실패해도 그날부터 빠진 스냅샷을 채운다 (#87 리뷰)
    import collectors.etf_holdings as etf

    seen = []
    monkeypatch.setattr(etf, "main", lambda argv: seen.append(argv) or 1)
    assert rd.collect_etf(date(2026, 11, 13)) == 1  # 실패 코드는 그대로 돌려준다 (B 요청 4)
    assert seen == [["backfill", "2026-11-13"]]


class FakeCursor:
    def __init__(self, rows, cols):
        self.rows, self.description = rows, [type("C", (), {"name": c}) for c in cols]

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class SourcesConn:
    """raw_sources·card_sources 를 들고 있는 가짜 연결. 자료 쿼리의 카드 제외 조건을 파이썬으로 흉내 낸다."""
    COLS = ["id", "source_type", "source_key", "category", "title", "url", "issuer_name", "ticker", "market",
            "published_date", "published_at", "numbers"]

    def __init__(self, sources, carded_ids):
        self.sources, self.carded, self.sql = sources, set(carded_ids), []

    def execute(self, sql, params):
        self.sql.append(" ".join(sql.split()))
        if "FROM prices" in sql:
            return FakeCursor([(date(2026, 11, 12),)], ["max"])
        prev, target = params
        excluded = self.carded if "NOT EXISTS (SELECT 1 FROM card_sources cs WHERE cs.source_id = r.id)" in self.sql[-1] else set()
        rows = [tuple(s.get(c) for c in self.COLS) for s in self.sources
                if prev < s["published_date"] <= target and s["id"] not in excluded]
        return FakeCursor(rows, self.COLS)


def test_sources_already_made_into_cards_are_skipped():
    # 같은 --date 로 다시 돌려도 이미 카드가 된 자료는 후보에서 빠진다 (#87 리뷰)
    d = date(2026, 11, 13)
    conn = SourcesConn([{"id": 1, "published_date": d, "title": "카드 된 자료"},
                        {"id": 2, "published_date": d, "title": "새 자료"},
                        {"id": 3, "published_date": date(2026, 11, 12), "title": "전 거래일 자료"}], carded_ids=[1])
    assert [s["id"] for s in rd.load_day_sources(conn, d)] == [2]


# --- 선별 점수 ---

def series(n_days: int, last_volume: float, last_close_jump: float = 0.0) -> pd.DataFrame:
    """평일 n_days 일. 거래량 100(마지막 날만 last_volume), 종가 100 고정(마지막 날만 +jump)."""
    days, d = [], date(2025, 6, 2)
    while len(days) < n_days:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    close = [100.0] * (n_days - 1) + [100.0 + last_close_jump]
    vol = [100.0] * (n_days - 1) + [last_volume]
    return pd.DataFrame({"market_date": days, "close": close, "volume": vol})


def test_own_scores_on_spike_day():
    # 과거 252일보다 거래량·수익률이 모두 가장 크면 2 + 2 = 4점
    s = series(254, last_volume=500, last_close_jump=3)
    assert rd.own_scores_on(s, s["market_date"].iloc[-1]) == {"vol_score": 2, "ret_score": 2, "score": 4}


def test_own_scores_on_day_without_data_is_zero():
    s = series(254, last_volume=500)
    assert rd.own_scores_on(s, s["market_date"].iloc[-1] + timedelta(days=1))["score"] == 0


def test_event_key_and_candidate():
    src = {"id": 5, "source_type": "macro", "category": "bok_rate", "ticker": None, "issuer_name": None,
           "published_date": date(2026, 11, 13), "published_at": None}
    assert rd.event_key(src) == "macro:bok_rate"
    c = rd.to_candidate(src, 1, 2)
    assert c.source_id == "5" and c.score == 3 and c.published_at.tzinfo is not None


class FakeScorer(rd.Scorer):
    """DB 대신 표를 넣어 둔 Scorer."""

    def __init__(self, calendar, kr_table=None, series_by_ticker=None):
        self.conn = None
        self._kr = {d: kr_table for d in calendar} if kr_table is not None else {}
        self._calendar = {"KS11": calendar, "IXIC": calendar, "KS11_": calendar}
        self.series_by_ticker = series_by_ticker or {}


def test_scorer_dart_takes_better_of_two_days(monkeypatch):
    # DART 는 시각이 없어 당일과 다음 거래일 중 큰 점수 (reaction_window_date_only)
    cal = [date(2026, 11, 12), date(2026, 11, 13)]
    scorer = FakeScorer(cal)
    tables = {cal[0]: pd.DataFrame({"vol_score": [0], "ret_score": [1]}, index=["005930"]),
              cal[1]: pd.DataFrame({"vol_score": [2], "ret_score": [1]}, index=["005930"])}
    monkeypatch.setattr(scorer, "kr_scores", lambda d: tables[d])
    src = {"market": "KR", "ticker": "005930", "published_date": cal[0], "published_at": None}
    assert scorer.score(src) == (2, 1)


def test_scorer_index_with_time_uses_reaction_day(monkeypatch):
    # 한은 발표 10:00 KST(장중) → KS11 은 당일만 본다. 다음 날 점수가 커도 쓰지 않는다
    cal = [date(2026, 10, 22), date(2026, 10, 23)]
    scorer = FakeScorer(cal)
    seen = []
    monkeypatch.setattr(rd, "load_series", lambda conn, t, d, n=300: seen.append(d) or pd.DataFrame())
    monkeypatch.setattr(rd, "own_scores_on", lambda s, d: {"vol_score": 0 if d == cal[0] else 2, "ret_score": 0})
    src = {"market": "INDEX", "ticker": "KS11", "published_date": cal[0],
           "published_at": datetime(2026, 10, 22, 10, 0, tzinfo=KST)}
    assert scorer.score(src) == (0, 0) and seen == [cal[0]]


def test_scorer_without_ticker_is_zero():
    assert FakeScorer([]).score({"market": None, "ticker": None, "published_date": date(2026, 11, 13)}) == (0, 0)


@pytest.mark.parametrize("today, want", [(date(2026, 11, 16), date(2026, 11, 13))])  # 월요일 → 금요일
def test_previous_trading_day(monkeypatch, today, want):
    import collectors.prices as prices

    monkeypatch.setattr(prices, "kr_trading_days", lambda end, n: [d for d in
                        [date(2026, 11, 12), date(2026, 11, 13)] if d <= end][-n:])
    assert rd.previous_trading_day(today) == want


# --- 장 마감 뒤 국내 가격 (홈 차트 O/X 정답용) ---

class _CloseConn:
    """count(*) 한 번만 묻는 가짜 연결."""

    def __init__(self, have):
        self.have = have

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        assert "market = 'KR'" in sql and params == (date(2026, 11, 26),)
        have = self.have

        class Cur:
            def fetchone(self):
                return (have,)

        return Cur()


def _patch_close(monkeypatch, have, kr_rows):
    import collectors.prices as prices
    import db

    calls = []
    monkeypatch.setattr(db, "get_conn", lambda: _CloseConn(have))
    monkeypatch.setattr(prices, "fetch_kr_daily", lambda d: calls.append(("kr", d)) or kr_rows)
    monkeypatch.setattr(prices, "fetch_index", lambda k, s, e: calls.append(("index", k, s, e)) or pd.DataFrame())
    monkeypatch.setattr(prices, "save_prices", lambda conn, df: len(df))
    return calls


def test_closing_prices_saves_today_kr_and_kr_indexes(monkeypatch):
    rows = pd.DataFrame({"ticker": ["277070", "005930"]})
    calls = _patch_close(monkeypatch, have=0, kr_rows=rows)

    out = rd.collect_closing_prices(date(2026, 11, 26))

    assert out == "국내 2026-11-26 2종목 + 국내 지수 2개"
    assert calls[0] == ("kr", date(2026, 11, 26))
    assert [c[1] for c in calls[1:]] == ["KS11", "KQ11"]   # 미국 지수는 아침에 받는다
    assert calls[1][2:] == (date(2026, 11, 16), date(2026, 11, 27))


def test_closing_prices_skips_when_already_collected(monkeypatch):
    calls = _patch_close(monkeypatch, have=rd.CLOSE_MIN_ROWS, kr_rows=pd.DataFrame())

    assert rd.collect_closing_prices(date(2026, 11, 26)) == f"국내 2026-11-26 이미 {rd.CLOSE_MIN_ROWS}종목"
    assert calls == []


def test_closing_prices_holiday_or_not_ready_is_zero_without_indexes(monkeypatch):
    calls = _patch_close(monkeypatch, have=0, kr_rows=pd.DataFrame())

    assert rd.collect_closing_prices(date(2026, 11, 26)) == "국내 2026-11-26 0종목 (휴장이거나 아직 자료 없음)"
    assert calls == [("kr", date(2026, 11, 26))]


def test_close_prices_flag_runs_only_price_step(monkeypatch, tmp_path):
    monkeypatch.setattr(rd, "LOG_PATH", tmp_path / "run_daily.jsonl")
    seen = []
    monkeypatch.setattr(rd, "collect_closing_prices", lambda d: seen.append(d) or "ok")
    monkeypatch.setattr(rd, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("run 을 부르면 안 된다")))

    assert rd.main(["--close-prices", "--date", "2026-11-26"]) == 0
    assert seen == [date(2026, 11, 26)]
    line = (tmp_path / "run_daily.jsonl").read_text(encoding="utf-8").strip()
    assert '"장 마감 국내 가격"' in line and '"target": "2026-11-26"' in line


def test_schedule_adds_morning_and_close_jobs(monkeypatch):
    blocking = pytest.importorskip("apscheduler.schedulers.blocking")  # pyproject 의존성. 옛 venv 면 건너뛴다

    jobs = []

    class FakeScheduler:
        def __init__(self, timezone):
            assert str(timezone) == "Asia/Seoul"

        def add_job(self, fn, trigger, hour, minute, misfire_grace_time):
            jobs.append((fn.__name__, hour, minute))

        def start(self):
            pass

    monkeypatch.setattr(blocking, "BlockingScheduler", FakeScheduler)
    rd.schedule()

    assert jobs == [("job", 8, 0), ("close_job", 15, 40), ("close_job", 16, 10), ("close_job", 17, 10)]
