"""concepts/ticker_loader.py 테스트. CSV 검사는 임시 폴더로, 재적재(upsert)는 로컬 DB 에서 되돌리는 트랜잭션으로 본다."""
import pytest

from concepts.loader import apply_seeds, read_seeds
from concepts.ticker_loader import HEADER, Mapping, apply_mappings, check_row, concept_ids, read_mappings

CONCEPTS = "id,name,theme,kind,aliases\ngpu_demand,AI 반도체 수요,AI·반도체,indicator,\nmemory_price,D램 가격,AI·반도체,indicator,\n"
HEAD = ",".join(HEADER) + "\n"
SRC = "https://www.sec.gov/x"
OK = f"gpu_demand,NVDA,US,GPU 를 판다,{SRC},draft\n"


def write(tmp_path, body, concepts=CONCEPTS, head=HEAD):
    (tmp_path / "concepts.csv").write_text(concepts, encoding="utf-8")
    (tmp_path / "concept_tickers.csv").write_text(head + body, encoding="utf-8")
    return tmp_path


def test_read_mappings(tmp_path):
    rows = read_mappings(write(tmp_path, OK + f"memory_price,005930,KR,D램을 만든다,{SRC},approved\n"))
    assert rows == [Mapping("gpu_demand", "NVDA", "US", "GPU 를 판다", SRC, "draft"),
                    Mapping("memory_price", "005930", "KR", "D램을 만든다", SRC, "approved")]


@pytest.mark.parametrize("ticker, market, ok", [
    ("NVDA", "US", True), ("BRK-B", "US", True),
    ("nvda", "US", False), ("BRK.B", "US", False), ("BRKB-", "US", False), ("", "US", False),
    ("005930", "KR", True), ("0015B0", "KR", True),   # 한국은 6자리 문자열, 영문 대문자 가능 (conventions 1장)
    ("5930", "KR", False), ("005930.KS", "KR", False), ("NVDA", "JP", False),
])
def test_ticker_format(ticker, market, ok):
    problems = check_row(Mapping("gpu_demand", ticker, market, "이유", SRC, "draft"), {"gpu_demand"})
    assert (problems == []) is ok


@pytest.mark.parametrize("body, message", [
    ("hbm_price,MU,US,이유,https://a,draft\n", "개념 사전에 없는 개념: hbm_price"),   # 이름이 비슷해도 사전 id 가 아니면 거부
    ("gpu_demand,NVDA,US,,https://a,draft\n", "reason 이 비었음"),
    ("gpu_demand,NVDA,US,이유,,draft\n", "source 는 https 링크"),
    ("gpu_demand,NVDA,US,이유,https://a,ok\n", "status 는"),
    (OK + OK.replace("draft", "approved"), "중복 행: gpu_demand,NVDA"),
])
def test_read_mappings_rejects(tmp_path, body, message):
    with pytest.raises(ValueError, match=message):
        read_mappings(write(tmp_path, body))


def test_read_mappings_reports_every_problem_with_line(tmp_path):
    with pytest.raises(ValueError) as e:
        read_mappings(write(tmp_path, OK + "없음,nvda,US,이유,https://a,draft\n"))
    assert "3줄 없음,nvda: 개념 사전에 없는 개념: 없음" in str(e.value)
    assert "3줄 없음,nvda: US 티커 형식이 아님: 'nvda'" in str(e.value)


def test_read_mappings_rejects_wrong_header(tmp_path):
    with pytest.raises(ValueError, match="머리줄"):
        read_mappings(write(tmp_path, OK, head="concept,ticker,market,reason,source,status\n"))


def test_real_seed_passes_check():
    # 실제 초안 (db/seeds/concept_tickers.csv): 개념 id 는 모두 B 의 사전에 있고 AI·반도체 테마만 쓴다
    rows = read_mappings()
    assert {m.concept_id for m in rows} <= concept_ids()
    assert {m.concept_id for m in rows} == {"ai_investment", "gpu_demand", "hbm_supply", "hbm_demand",
                                           "memory_price", "semi_earnings"}
    assert all(m.status == "draft" for m in rows)   # 팀 검토 전
    # ai_investment 는 투자하는 쪽에만 붙인다. 돈 버는 쪽(NVDA 등)은 gpu_demand·semi_earnings
    assert {m.ticker for m in rows if m.concept_id == "ai_investment"} == {"GOOGL", "MSFT", "AMZN", "META"}


@pytest.fixture
def db_conn():
    """로컬 DB 에 005 가 적용돼 있을 때만. 끝나면 되돌린다."""
    psycopg = pytest.importorskip("psycopg")
    from db import get_conn
    try:
        conn = get_conn()
    except psycopg.OperationalError:
        pytest.skip("로컬 DB 에 연결할 수 없음")
    if conn.execute("SELECT to_regclass('concept_tickers')").fetchone()[0] is None:
        conn.close()
        pytest.skip("concept_tickers 테이블 없음 (005 마이그레이션 적용 필요)")
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def test_reapply_is_idempotent_on_real_db(db_conn):
    apply_seeds(db_conn, read_seeds())   # FK 용 개념 사전 (같은 트랜잭션, 되돌림)
    db_conn.execute("DELETE FROM concept_tickers")
    rows = read_mappings()

    first = apply_mappings(db_conn, rows)
    second = apply_mappings(db_conn, rows)   # 두 번째는 아무것도 바뀌지 않는다

    assert len(first["inserted"]) == len(rows) and first["updated"] == [] and first["removed"] == []
    assert second == {"inserted": [], "updated": [], "removed": []}
    assert db_conn.execute("SELECT count(*) FROM concept_tickers").fetchone()[0] == len(rows)

    # 이유를 고친 행은 바뀜, CSV 에서 뺀 행은 지움
    changed = [Mapping(**{**rows[0].__dict__, "reason": "고친 이유"})] + rows[2:]
    third = apply_mappings(db_conn, changed)
    assert third["updated"] == [(rows[0].concept_id, rows[0].ticker)]
    assert third["removed"] == [(rows[1].concept_id, rows[1].ticker)]
    assert db_conn.execute("SELECT count(*) FROM concept_tickers").fetchone()[0] == len(rows) - 1


def test_apply_asks_to_load_dictionary_first(db_conn):
    # 개념이 DB concepts 에 없으면 FK 오류 대신 할 일을 알려 준다.
    # DB 의 개념을 지우면 cards·user_concepts 가 참조할 때 FK 에 걸리므로, DB 에 없는 id 로 시험한다
    missing = "zz_not_loaded_concept"
    assert not db_conn.execute("SELECT 1 FROM concepts WHERE id = %s", (missing,)).fetchone()
    with pytest.raises(ValueError, match=f"DB concepts 에 없는 개념: {missing}.*concepts.loader --save"):
        apply_mappings(db_conn, [Mapping(missing, "NVDA", "US", "이유", SRC, "draft")])


def test_db_rejects_bad_ticker_format(db_conn):
    # 005 의 CHECK 가 loader 검사와 같은 규칙인지 (CSV 를 거치지 않고 넣어도 막힌다)
    apply_seeds(db_conn, read_seeds())
    psycopg = pytest.importorskip("psycopg")
    with pytest.raises(psycopg.errors.CheckViolation):
        db_conn.execute("INSERT INTO concept_tickers (concept_id, ticker, market, reason, source) "
                        "VALUES ('gpu_demand', 'BRK.B', 'US', '이유', 'https://a')")
