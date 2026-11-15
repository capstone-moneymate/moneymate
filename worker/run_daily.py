"""하루 파이프라인 (C). 수집 → 계산 → 선별 → 출제(검증 포함) → pending 저장을 한 번에 돌린다.

실행 (worker/ 에서):
    python run_daily.py                       # 지난 국내 거래일 기준 한 번
    python run_daily.py --date 2026-11-13     # 그날 기준 (다시 돌리기)
    python run_daily.py --no-llm              # 수집·선별 점수까지만 (Claude 호출 없음, 비용 0)
    python run_daily.py --skip-collect        # 수집은 건너뛰고 DB 에 있는 것으로 선별·출제
    python run_daily.py --schedule            # 매일 08:00 KST 에 실행 (APScheduler, 멈출 때까지)

언제: 아침 08:00 KST. 그때면 전날 국내 장(15:30 마감)과 DART 공시, 미국 장(한국 시각 새벽 마감)이 다 나와 있다.
기준일(target)은 오늘 이전 가장 최근 국내 거래일이다. 카드 날짜는 실행한 날(오늘).

원칙
- 단계 하나가 실패해도 나머지는 계속 돌리고, 마지막에 실패가 있으면 종료 코드 1 (cron·스케줄러가 알 수 있게).
- ETF 수집기는 실패하면 1을 돌려준다 (B 요청 4). 그 값을 그대로 단계 실패로 본다.
- 선별 점수는 compute/source_select.py 의 함수를 쓰고, 여기서는 DB 에서 표를 읽어 넘기기만 한다.
- Claude 는 점수 1점 이상 후보만 분류(Haiku)하고, 고른 최대 3건만 출제(Sonnet)한다.
"""
import argparse
import json
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config  # noqa: F401  .env 를 읽는다
from compute.source_select import (Candidate, cross_section_scores, own_history_score,
                                   reaction_day, reaction_window_date_only, select)

KST = ZoneInfo("Asia/Seoul")
LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "run_daily.jsonl"
MAX_CARDS = 3  # 하루 카드 수 (기술확정안 "고르기 최대 3건")
MAX_CLASSIFY = 10  # Haiku 분류 상한 (점수 높은 순). 비용을 묶는다
SCHEDULE_TIME = (8, 0)  # KST
# 지수 → 장 마감 시각을 볼 시장 (collectors/prices.py INDEXES 와 같은 키)
INDEX_MARKET = {"KS11": "KR", "KQ11": "KR", "IXIC": "US", "US500": "US"}


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class DailyReport:
    target: str
    started_at: str
    steps: list[StepResult] = field(default_factory=list)
    card_ids: list[int] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


def run_step(report: DailyReport, name: str, fn, *args):
    """fn 을 실행하고 결과를 기록한다. 예외도 실패로 남기고 다음 단계로 간다. fn 이 int 를 돌려주면 0이 성공."""
    try:
        out = fn(*args)
    except Exception as e:  # 한 단계가 죽어도 하루 파이프라인은 계속 간다
        traceback.print_exc()
        report.steps.append(StepResult(name, False, f"{e.__class__.__name__}: {e}"))
        return None
    if isinstance(out, int) and not isinstance(out, bool) and out != 0:
        report.steps.append(StepResult(name, False, f"종료 코드 {out}"))
    else:
        report.steps.append(StepResult(name, True, out if isinstance(out, str) else ""))
    print(f"[{'OK ' if report.steps[-1].ok else 'ERR'}] {name} {report.steps[-1].detail}")
    return out


# ------------------------------------------------------------------
# 1. 수집·계산 (각 모듈의 함수·main 을 그대로 부른다)
# ------------------------------------------------------------------

def collect_prices(target: date) -> str:
    from collectors.prices import INDEXES, fetch_index, fetch_kr_daily, save_prices
    from db import get_conn

    with get_conn() as conn:
        n = save_prices(conn, fetch_kr_daily(target))
        for key in INDEXES:
            save_prices(conn, fetch_index(key, target - timedelta(days=10), target + timedelta(days=1)))
    return f"국내 {target} {n}종목 + 지수 {len(INDEXES)}개"


def watch_us_tickers() -> list[str]:
    """8-K 를 볼 미국 종목: 탭 2 에 나오는 종목 (가장 최근 겹침 결과). 없으면 빈 목록."""
    from db import get_conn

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT ticker FROM overlap_results
               WHERE calc_date = (SELECT max(calc_date) FROM overlap_results)"""
        ).fetchall()
    return sorted(r[0] for r in rows if r[0] and not r[0].isdigit())


def collect_sources(target: date) -> int:
    from collectors import sources

    code = sources.main(["dart", target.isoformat(), "--save"])
    code |= sources.main(["macro", target.isoformat(), "--save"])
    us = watch_us_tickers()
    if us:
        code |= sources.main(["sec", target.isoformat(), *us, "--save"])
    return code


def collect_etf() -> int:
    from collectors import etf_holdings

    return etf_holdings.main(["today"])  # 실패하면 1 (B 요청 4)


def compute_etf_trend(target: date) -> int:
    from compute import etf_trend

    return etf_trend.main(["--date", target.isoformat(), "--save"])


# ------------------------------------------------------------------
# 2. 선별 점수 (DB 표 → source_select 함수)
# ------------------------------------------------------------------

def load_series(conn, ticker: str, until: date, n: int = 300) -> pd.DataFrame:
    """그 종목의 until 이하 마지막 n 거래일. 컬럼 market_date, close, volume (오름차순)."""
    rows = conn.execute(
        """SELECT market_date, close, volume FROM prices WHERE ticker = %s AND market_date <= %s
           ORDER BY market_date DESC LIMIT %s""",
        (ticker, until, n),
    ).fetchall()
    df = pd.DataFrame(rows, columns=["market_date", "close", "volume"]).iloc[::-1].reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    return df


def own_scores_on(series: pd.DataFrame, day: date) -> dict:
    """지수·미국 종목: 그날까지의 거래량·일간 수익률로 자기 과거 252일 대비 점수 (source_select.own_history_score)."""
    s = series[series["market_date"] <= day]
    if s.empty or s["market_date"].iloc[-1] != day:
        return {"vol_score": 0, "ret_score": 0, "score": 0}
    returns = s["close"].pct_change().dropna().tolist()
    return own_history_score(s["volume"].astype(float).tolist(), returns)


def kr_day_table(conn, day: date) -> pd.DataFrame:
    """그날 국내 전 종목 ticker, volume, chg_pct (전 거래일 종가 대비 %)."""
    rows = conn.execute(
        """SELECT p.ticker, p.volume, (p.close / prev.close - 1) * 100
           FROM prices p
           JOIN LATERAL (SELECT close FROM prices q WHERE q.ticker = p.ticker AND q.market_date < p.market_date
                         ORDER BY q.market_date DESC LIMIT 1) prev ON true
           WHERE p.market = 'KR' AND p.market_date = %s AND prev.close > 0""",
        (day,),
    ).fetchall()
    df = pd.DataFrame(rows, columns=["ticker", "volume", "chg_pct"])
    df["chg_pct"] = df["chg_pct"].astype(float)
    return df


class Scorer:
    """반응일마다 국내 전 종목 점수표를 한 번만 만든다."""

    def __init__(self, conn):
        self.conn = conn
        self._kr: dict[date, pd.DataFrame] = {}
        self._calendar: dict[str, list[date]] = {}

    def calendar(self, market: str, ticker: str | None) -> list[date]:
        key = "KS11" if market == "KR" else ("IXIC" if market == "US" else ticker)
        if key not in self._calendar:
            self._calendar[key] = load_series(self.conn, key, date.today(), 400)["market_date"].tolist()
        return self._calendar[key]

    def kr_scores(self, day: date) -> pd.DataFrame:
        if day not in self._kr:
            from collectors.prices import load_volume_history

            table = kr_day_table(self.conn, day)
            history = load_volume_history(self.conn, table["ticker"].tolist(), day)
            self._kr[day] = cross_section_scores(table, history).set_index("ticker")
        return self._kr[day]

    def score(self, src: dict) -> tuple[int, int]:
        """(거래량 점수, 수익률 점수). 반응일 후보 중 합이 가장 큰 날. 볼 종목이 없으면 (0, 0)."""
        market, ticker = src.get("market"), src.get("ticker")
        if not ticker or market not in ("KR", "US", "INDEX"):
            return 0, 0
        days_cal = self.calendar(market, ticker)
        close_market = INDEX_MARKET.get(ticker) if market == "INDEX" else market  # 지수는 그 시장의 마감 시각
        if src.get("published_at") and close_market in ("KR", "US"):
            day = reaction_day(src["published_at"], close_market, days_cal)
            days = [day] if day else []
        else:  # DART·거시 발표처럼 시각을 모르면 당일과 다음 거래일 (데이터가 있는 날만)
            days = reaction_window_date_only(src["published_date"], days_cal)
        best = (0, 0)
        for d in days:
            if market == "KR":
                table = self.kr_scores(d)
                row = table.loc[ticker] if ticker in table.index else None
                s = (int(row["vol_score"]), int(row["ret_score"])) if row is not None else (0, 0)
            else:
                o = own_scores_on(load_series(self.conn, ticker, d), d)
                s = (o["vol_score"], o["ret_score"])
            best = max(best, s, key=sum)
        return best


def load_day_sources(conn, target: date) -> list[dict]:
    """기준일(target) 직전 거래일 다음 날부터 target 까지 나온 1차 자료. 주말·휴일 발표도 다음 거래일에 잡힌다."""
    prev = conn.execute(
        "SELECT max(market_date) FROM prices WHERE ticker = 'KS11' AND market_date < %s", (target,)
    ).fetchone()[0] or target - timedelta(days=1)
    cur = conn.execute(
        """SELECT id, source_type, source_key, category, title, url, issuer_name, ticker, market,
                  published_date, published_at, numbers
           FROM raw_sources WHERE published_date > %s AND published_date <= %s ORDER BY id""",
        (prev, target),
    )
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def event_key(src: dict) -> str:
    """같은 회사·사건 판정 (source_select.select 가 1건만 남긴다). 회사는 종목, 거시는 분류."""
    return src.get("ticker") or src.get("issuer_name") or f"{src['source_type']}:{src['category']}"


def to_candidate(src: dict, vol: int, ret: int) -> Candidate:
    published = src.get("published_at") or datetime.combine(src["published_date"], datetime.min.time(), KST)
    return Candidate(source_id=str(src["id"]), event_key=event_key(src), published_at=published,
                     vol_score=vol, ret_score=ret, extra={"source": src})


def score_sources(target: date) -> list[Candidate]:
    from db import get_conn

    with get_conn() as conn:
        sources = load_day_sources(conn, target)
        scorer = Scorer(conn)
        cands = [to_candidate(s, *scorer.score(s)) for s in sources]
    print(f"  자료 {len(cands)}건, 1점 이상 {sum(c.score >= 1 for c in cands)}건")
    return cands


# ------------------------------------------------------------------
# 3. 분류(Haiku) → 고르기 → 출제(Sonnet, 검증·pending 저장 포함)
# ------------------------------------------------------------------

def classify_candidates(cands: list[Candidate]) -> list[Candidate]:
    """점수 1점 이상 중 상위 MAX_CLASSIFY 건만 분류한다. card_type·start_concept·theme 을 채운다."""
    from generate.classify import classify, load_concepts, load_edges, load_etf_tickers

    concepts, edges, etf = load_concepts(), load_edges(), load_etf_tickers()
    theme = {c.id: c.theme for c in concepts}
    top = sorted((c for c in cands if c.score >= 1), key=lambda c: -c.score)[:MAX_CLASSIFY]
    for c in top:
        r = classify(c.extra["source"], concepts, edges, etf)
        c.card_type, c.start_concept, c.theme = r.card_type, r.start_concept, theme.get(r.start_concept)
        c.extra["classify"] = r
    return top


def compose_selected(picked: list[Candidate], card_date: date) -> list[int]:
    from generate.compose import compose

    ids = []
    for c in picked:
        res = compose(c.extra["source"], c.extra["classify"], card_date)
        print(f"  {c.extra['source']['title'][:30]} → card_id={res.card_id} 호출 {res.calls}회 "
              f"${res.cost_usd:.3f} {('; '.join(res.errors))[:120]}")
        if res.card_id:
            ids.append(res.card_id)
    if picked and not ids:
        raise RuntimeError("고른 자료로 카드를 하나도 만들지 못했어요")
    return ids


# ------------------------------------------------------------------
# 실행
# ------------------------------------------------------------------

def previous_trading_day(today: date) -> date:
    from collectors.prices import kr_trading_days

    return kr_trading_days(today - timedelta(days=1), 1)[-1]


def run(target: date, card_date: date, collect: bool = True, llm: bool = True) -> DailyReport:
    report = DailyReport(target.isoformat(), datetime.now(KST).isoformat(timespec="seconds"))
    if collect:
        run_step(report, "가격", collect_prices, target)
        run_step(report, "1차 자료", collect_sources, target)
        run_step(report, "ETF 구성종목", collect_etf)
        run_step(report, "ETF 추세", compute_etf_trend, target)
    cands = run_step(report, "선별 점수", score_sources, target) or []
    if llm and cands:
        top = run_step(report, "분류", classify_candidates, cands) or []
        picked = select(top, MAX_CARDS)
        print(f"  고른 자료 {len(picked)}건: " + ", ".join(c.extra["source"]["title"][:20] for c in picked))
        report.card_ids = run_step(report, "출제", compose_selected, picked, card_date) or []
    write_log(report)
    print(f"\n{'완료' if report.ok else '실패한 단계가 있어요'}: 카드 {report.card_ids or '없음'}")
    return report


def write_log(report: DailyReport, path: Path | None = None) -> None:
    path = path or LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({**asdict(report), "ok": report.ok}, ensure_ascii=False) + "\n")


def schedule() -> None:
    """매일 SCHEDULE_TIME(KST)에 run. 프로세스가 떠 있는 동안만 돈다 (배포 때는 컨테이너로 띄운다)."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    sched = BlockingScheduler(timezone=KST)

    def job():
        today = datetime.now(KST).date()
        run(previous_trading_day(today), today)

    sched.add_job(job, "cron", hour=SCHEDULE_TIME[0], minute=SCHEDULE_TIME[1], misfire_grace_time=3600)
    print(f"매일 {SCHEDULE_TIME[0]:02d}:{SCHEDULE_TIME[1]:02d} KST 에 실행합니다. 멈추려면 Ctrl+C")
    sched.start()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="하루 파이프라인")
    parser.add_argument("--date", help="기준 거래일 YYYY-MM-DD (없으면 오늘 이전 가장 최근 국내 거래일)")
    parser.add_argument("--skip-collect", action="store_true", help="수집·계산을 건너뛴다")
    parser.add_argument("--no-llm", action="store_true", help="분류·출제를 건너뛴다 (Claude 호출 없음)")
    parser.add_argument("--schedule", action="store_true", help="매일 08:00 KST 에 실행")
    args = parser.parse_args(argv)
    if args.schedule:
        schedule()
        return 0
    today = datetime.now(KST).date()
    target = date.fromisoformat(args.date) if args.date else previous_trading_day(today)
    report = run(target, today, collect=not args.skip_collect, llm=not args.no_llm)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
