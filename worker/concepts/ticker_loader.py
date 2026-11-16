"""개념↔티커 매핑 적재 (A, #100). db/seeds/concept_tickers.csv 를 concept_tickers 테이블(005)에 넣는다.

실행 (worker/ 에서):
    python -m concepts.ticker_loader          # 적재해 보고 결과만 출력 (되돌림)
    python -m concepts.ticker_loader --save   # DB 에 반영

규칙 (conventions P20, docs/modules/ticker_loader.md)
- CSV 가 원본이다. 여러 번 돌려도 결과가 같다 (upsert). CSV 에서 지운 행은 DB 에서도 지운다
- 개념 id 는 B 의 concepts.csv 에 있는 것만. 탭 2 가 user_concepts.concept_id 와 그대로 비교하기 때문이다
- 넣기 전에 검사한다: 사전에 없는 개념, 티커 형식(conventions 1장), 시장 값, 근거 링크, 상태 값, 중복 행
"""
import argparse
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from concepts.graph import SEEDS

HEADER = ["concept_id", "ticker", "market", "reason", "source", "status"]
MARKETS = ("US", "KR")
STATUSES = ("draft", "approved")
# 005 마이그레이션의 CHECK 와 같은 식. 미국은 대문자(클래스주 하이픈), 한국은 6자리 문자열(영문 대문자 가능)
TICKER_FORMAT = {"US": re.compile(r"[A-Z]+(-[A-Z]+)?"), "KR": re.compile(r"[0-9A-Z]{6}")}


@dataclass(frozen=True)
class Mapping:
    concept_id: str
    ticker: str
    market: str
    reason: str
    source: str
    status: str


def concept_ids(seeds_dir: Path = SEEDS) -> set[str]:
    """B 의 개념 사전(concepts.csv)에 있는 id."""
    with open(seeds_dir / "concepts.csv", encoding="utf-8", newline="") as f:
        return {r["id"] for r in csv.DictReader(f)}


def check_row(m: Mapping, known: set[str]) -> list[str]:
    """한 줄의 문제를 모두 돌려준다. 비어 있으면 통과."""
    problems = []
    if m.concept_id not in known:
        problems.append(f"개념 사전에 없는 개념: {m.concept_id}")
    if m.market not in MARKETS:
        problems.append(f"market 은 {MARKETS} 중 하나: {m.market!r}")
    elif not TICKER_FORMAT[m.market].fullmatch(m.ticker):
        problems.append(f"{m.market} 티커 형식이 아님: {m.ticker!r}")
    if not m.reason.strip():
        problems.append("reason 이 비었음")
    if not m.source.startswith("https://"):
        problems.append(f"source 는 https 링크여야 함: {m.source!r}")
    if m.status not in STATUSES:
        problems.append(f"status 는 {STATUSES} 중 하나: {m.status!r}")
    return problems


def read_mappings(seeds_dir: Path = SEEDS) -> list[Mapping]:
    """CSV 를 읽고 검사한다. 하나라도 잘못됐으면 DB 에 넣기 전에 ValueError (문제를 전부 모아서)."""
    with open(seeds_dir / "concept_tickers.csv", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != HEADER:
            raise ValueError(f"머리줄이 {HEADER} 이어야 함: {reader.fieldnames}")
        rows = [Mapping(*(r[k] for k in HEADER)) for r in reader]

    known = concept_ids(seeds_dir)
    problems = []
    for line, m in enumerate(rows, start=2):  # 1줄은 머리줄
        problems += [f"{line}줄 {m.concept_id},{m.ticker}: {p}" for p in check_row(m, known)]
    repeated = [k for k, n in Counter((m.concept_id, m.ticker) for m in rows).items() if n > 1]
    problems += [f"중복 행: {c},{t}" for c, t in repeated]
    if problems:
        raise ValueError("concept_tickers.csv 검사 실패\n  " + "\n  ".join(problems))
    return rows


def apply_mappings(conn, rows: list[Mapping]) -> dict[str, list]:
    """DB 를 CSV 와 똑같이 맞춘다. 커밋은 부르는 쪽이 한다.
    값이 같은 행은 건드리지 않아 updated_at 이 그대로다. 새로 넣은 행·바꾼 행·지운 행을 돌려준다."""
    inserted, updated = [], []
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM concepts")
        missing = sorted({m.concept_id for m in rows} - {c for (c,) in cur.fetchall()})
        if missing:  # FK 오류 대신 할 일을 알려 준다
            raise ValueError(f"DB concepts 에 없는 개념: {', '.join(missing)}. "
                             "먼저 python -m concepts.loader --save 로 개념 사전을 적재하세요")
        for m in rows:
            cur.execute(
                """INSERT INTO concept_tickers (concept_id, ticker, market, reason, source, status)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (concept_id, ticker) DO UPDATE SET market = EXCLUDED.market,
                       reason = EXCLUDED.reason, source = EXCLUDED.source, status = EXCLUDED.status,
                       updated_at = now()
                   WHERE (concept_tickers.market, concept_tickers.reason, concept_tickers.source,
                          concept_tickers.status)
                         IS DISTINCT FROM (EXCLUDED.market, EXCLUDED.reason, EXCLUDED.source, EXCLUDED.status)
                   RETURNING (xmax = 0) AS inserted""",
                (m.concept_id, m.ticker, m.market, m.reason, m.source, m.status),
            )
            got = cur.fetchone()  # 값이 같아 건너뛰면 None
            if got is not None:
                (inserted if got[0] else updated).append((m.concept_id, m.ticker))

        wanted = {(m.concept_id, m.ticker) for m in rows}
        cur.execute("SELECT concept_id, ticker FROM concept_tickers")
        removed = sorted(k for k in map(tuple, cur.fetchall()) if k not in wanted)
        for concept_id, ticker in removed:
            cur.execute("DELETE FROM concept_tickers WHERE concept_id = %s AND ticker = %s", (concept_id, ticker))
    return {"inserted": inserted, "updated": updated, "removed": removed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="개념↔티커 매핑 CSV 를 DB 에 적재")
    parser.add_argument("--save", action="store_true", help="DB 에 반영 (없으면 적재 후 되돌림)")
    args = parser.parse_args(argv)
    rows = read_mappings()

    from db import get_conn
    conn = get_conn()
    try:
        result = apply_mappings(conn, rows)
        print(f"매핑 {len(rows)}줄 (개념 {len({m.concept_id for m in rows})}개, 종목 {len({m.ticker for m in rows})}개)")
        print(f"  새로 넣음 {len(result['inserted'])}, 바꿈 {len(result['updated'])}, 지움 {len(result['removed'])}")
        for concept_id, ticker in result["removed"]:
            print(f"  지운 행: {concept_id},{ticker}")
        if args.save:
            conn.commit()
            print("\nDB 에 반영했습니다.")
        else:
            conn.rollback()
            print("\n출력만 했습니다. 반영하려면 --save 를 붙이세요.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
