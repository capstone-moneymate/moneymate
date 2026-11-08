"""concepts/loader.py 테스트. CSV 검사는 임시 폴더로, DB 쓰기는 가짜 연결로 확인한다."""
import pytest

from concepts.loader import Seeds, apply_seeds, parse_aliases, read_seeds

CONCEPTS = "id,name,theme,kind,aliases\na,가,금리,event,가1;가2\nb,나,금리,outcome,\n"
EDGES = "from_concept,to_concept,force_dir,note\na,b,up,설명\n"


def write_seeds(tmp_path, concepts=CONCEPTS, edges=EDGES):
    (tmp_path / "concepts.csv").write_text(concepts, encoding="utf-8")
    (tmp_path / "causal_edges.csv").write_text(edges, encoding="utf-8")
    return tmp_path


def test_parse_aliases():
    assert parse_aliases("금리 인상; 금리 올림") == ["금리 인상", "금리 올림"]
    assert parse_aliases("") == []


def test_read_seeds(tmp_path):
    seeds = read_seeds(write_seeds(tmp_path))
    assert seeds.concepts == [("a", "가", "금리", "event", ["가1", "가2"]), ("b", "나", "금리", "outcome", [])]
    assert seeds.edges == [("a", "b", "up", "설명")]


@pytest.mark.parametrize("concepts, edges, message", [
    (CONCEPTS + "a,또,금리,event,\n", EDGES, "개념 id 가 중복됨: a"),
    (CONCEPTS, EDGES + "a,b,down,다시\n", "연결이 중복됨: a -> b"),
    (CONCEPTS, EDGES + "a,없음,up,\n", "개념 사전에 없는 개념: 없음"),
    (CONCEPTS, EDGES + "b,a,sideways,\n", "force_dir"),
    (CONCEPTS, EDGES + "b,a,up,\n", "순환"),
])
def test_read_seeds_rejects_bad_dictionary(tmp_path, concepts, edges, message):
    with pytest.raises(ValueError, match=message):
        read_seeds(write_seeds(tmp_path, concepts, edges))


def test_real_seeds_pass_check():
    # 실제 사전 (db/seeds). 보류했던 연결 2개를 지운 뒤 17개 / 14개
    seeds = read_seeds()
    assert (len(seeds.concepts), len(seeds.edges)) == (17, 14)
    pairs = {e[:2] for e in seeds.edges}
    assert ("rate_hike", "growth_valuation") not in pairs and ("rate_cut", "ai_investment") not in pairs


class FakeCursor:
    """SELECT 는 넣어 둔 줄을 돌려주고, 나머지 SQL 은 모은다."""

    def __init__(self, rows):
        self.rows, self.calls, self.result = rows, [], []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
        for key, rows in self.rows.items():
            if sql.startswith(key):
                self.result = rows

    def fetchall(self):
        return self.result


class FakeConn:
    def __init__(self, rows):
        self.cur = FakeCursor(rows)

    def cursor(self):
        return self.cur


def test_apply_seeds_syncs_edges_and_keeps_extra_concepts():
    seeds = Seeds([("a", "가", "금리", "event", ["가1"]), ("b", "나", "금리", "outcome", [])],
                  [("a", "b", "up", "설명")])
    conn = FakeConn({
        "SELECT from_concept": [("a", "b"), ("b", "a")],   # b -> a 는 CSV 에서 지운 연결
        "SELECT id": [("a",), ("b",), ("old",)],           # old 는 CSV 에서 지운 개념
    })
    assert apply_seeds(conn, seeds) == {"removed_edges": [("b", "a")], "extra_concepts": ["old"]}

    calls = conn.cur.calls
    deletes = [c for c in calls if c[0].startswith("DELETE")]
    assert [d[1] for d in deletes] == [("b", "a")]
    assert not any("DELETE FROM concepts" in c[0] for c in calls)       # 개념은 지우지 않는다
    inserts = [c[0] for c in calls if c[0].startswith("INSERT")]
    assert len(inserts) == 3 and all("ON CONFLICT" in s for s in inserts)
    assert calls[0][1] == ("a", "가", "금리", "event", ["가1"])          # 별칭은 목록으로 (TEXT[])
