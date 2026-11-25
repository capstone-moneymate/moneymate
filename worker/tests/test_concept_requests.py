"""concepts/concept_requests.py: 개념 지도에 없는 새 용어 요청 (#266). 실제 API 는 부르지 않는다 (ask 를 가짜로).
new_terms·run 은 실제 PostgreSQL(009)에서 보고 끝에 rollback 한다. DB 가 없으면 건너뛴다."""
import json
import uuid
from datetime import datetime, timezone

import pytest

from concepts import concept_requests as cr
from concepts.concept_map import ReviewRow, load_review, save_review
from concepts.prereq_votes import PrereqRow, load_prereq_review, save_prereq_review

ITEM = {"card_id": 32, "term": "생산능력", "card_desc": "공장이 만들 수 있는 최대 양"}


def fake_ask(*answers):
    queue = list(answers)
    return lambda item, names: queue.pop(0)


def test_schema_names_are_enum_only():
    s = cr.schema(["매출액", "자기자본"])
    assert s["properties"]["same_as"]["enum"] == ["", "매출액", "자기자본"]
    assert s["properties"]["pre_1"]["enum"] == s["properties"]["pre_2"]["enum"] == ["", "매출액", "자기자본"]


def test_suggest_needs_two_same_answers():
    a = {"same_as": "", "desc": "최대 생산량", "pre_1": "신규 시설투자", "pre_2": ""}
    b = {"same_as": "", "desc": "표현만 다름", "pre_1": "", "pre_2": "신규 시설투자"}   # 순서·뜻 문장은 달라도 된다
    r = cr.suggest(ITEM, [], fake_ask(a, b))
    assert r["agreed"] and r["suggestion"] == {"same_as": "", "desc": "최대 생산량", "prereqs": ["신규 시설투자"]}
    c = {"same_as": "", "desc": "x", "pre_1": "매출액", "pre_2": ""}
    r = cr.suggest(ITEM, [], fake_ask(a, c))                                              # 선수 개념이 다르면
    assert not r["agreed"] and r["suggestion"] is None and r["term"] == "생산능력"        # 용어는 남긴다
    d = {"same_as": "", "desc": "x", "pre_1": "생산능력", "pre_2": ""}                     # 자기 자신은 선수 개념이 아니다
    assert cr.suggest(ITEM, [], fake_ask(d, d))["suggestion"]["prereqs"] == []


def test_to_review_adds_blank_rows_once(tmp_path):
    tp, pp = tmp_path / "t.csv", tmp_path / "p.csv"
    save_review([ReviewRow("자사주", "same", "자기주식")], tp)
    save_prereq_review([PrereqRow("매출액", "영업이익", "keep", "4/4")], pp)
    reqs = [{"requested_at": "2026-11-26T00:00:00+00:00", "card_id": 32, "term": "생산능력", "card_desc": "c",
             "agreed": True, "suggestion": {"same_as": "", "desc": "최대 생산량", "prereqs": ["신규 시설투자"]}},
            {"requested_at": "2026-11-26T00:00:00+00:00", "card_id": 33, "term": "설비 투자", "card_desc": "c",
             "agreed": True, "suggestion": {"same_as": "신규 시설투자", "desc": "d", "prereqs": ["매출액"]}},
            {"requested_at": "2026-11-26T00:00:00+00:00", "card_id": 34, "term": "가동률", "card_desc": "카드 뜻",
             "agreed": False, "suggestion": None}]
    assert cr.to_review(reqs, tp, pp) == {"terms": 3, "prereqs": 1}
    t = {r.term: r for r in load_review(tp)}
    assert t["생산능력"].decision == "" and "새 개념" in t["생산능력"].note
    assert t["설비 투자"].decision == "" and t["설비 투자"].same_as == "신규 시설투자"   # 사람이 same 을 적어야 합쳐진다
    assert t["가동률"].desc == "카드 뜻" and "제안 없음" in t["가동률"].note
    p = load_prereq_review(pp)
    assert [(r.pre, r.post, r.decision, r.votes) for r in p[1:]] == [("신규 시설투자", "생산능력", "", "2/2")]
    assert cr.to_review(reqs, tp, pp) == {"terms": 0, "prereqs": 0}   # 두 번 불러도 같다


# --- DB ---

@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT 1 FROM concept_nodes LIMIT 0")
    except Exception as e:  # DB 없음, 009 미적용
        pytest.skip(f"009 가 적용된 DB 가 필요해요: {e}")
    c.rollback()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def test_run_finds_only_new_terms_and_appends(conn, tmp_path):
    tag = uuid.uuid4().hex[:8]
    conn.execute("INSERT INTO concept_nodes (label, aliases) VALUES (%s, %s)", (f"있는말{tag}", [f"별칭{tag}"]))
    cid = conn.execute("""INSERT INTO cards (card_date, card_type, title, slides) VALUES ('2026-11-26', 1, '시험', '[]')
                          RETURNING id""").fetchone()[0]
    terms = [{"term": f"있는 말{tag}", "desc": "a"}, {"term": f"별칭{tag}(%)", "desc": "b"},   # 띄어쓰기·괄호 무시로 있음
             {"term": f"새말{tag}", "desc": "c"}, {"term": f"새 말{tag}", "desc": "d"}]          # 같은 새 용어는 하나만
    conn.execute("INSERT INTO steps (card_id, step_no, kind, content) VALUES (%s, 1, 'concept', %s)",
                 (cid, json.dumps({"terms": terms}, ensure_ascii=False)))
    path = tmp_path / "req.jsonl"
    ans = {"same_as": "", "desc": "뜻", "pre_1": f"있는말{tag}", "pre_2": ""}
    now = datetime(2026, 11, 26, tzinfo=timezone.utc)
    out = cr.run(conn, [cid], path, ask=lambda item, names: ans, now=now)
    assert [r["term"] for r in out] == [f"새말{tag}"] and out[0]["suggestion"]["prereqs"] == [f"있는말{tag}"]
    assert cr.load_requests(path)[0]["requested_at"] == "2026-11-26T00:00:00+00:00"
    assert cr.run(conn, [cid], path, ask=lambda item, names: ans) == []   # 이미 요청한 용어는 다시 묻지 않는다
