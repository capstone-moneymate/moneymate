"""concepts/proposals.py 테스트. 실제 API 는 부르지 않는다 (create 를 가짜로 바꾼다)."""
import json
from types import SimpleNamespace

import pytest

from concepts import proposals as pr
from concepts.graph import build_graph

CONCEPTS = [
    {"id": "rate_hike", "name": "기준금리 인상", "theme": "금리", "kind": "event", "aliases": "금리 인상;금리 올림"},
    {"id": "bond_yield", "name": "국채 금리", "theme": "금리", "kind": "indicator", "aliases": "시장금리"},
]
GRAPH = build_graph({"rate_hike": "기준금리 인상", "bond_yield": "국채 금리"}, [("rate_hike", "bond_yield", "up")])
SOURCE = {"title": "원/달러 환율 1,500원 돌파", "category": "fx_rate"}


def payload(cid="fx_rate", name="원/달러 환율", aliases=("환율",), edges=None):
    if edges is None:
        edges = [{"existing": "rate_hike", "position": "existing_to_new", "force_dir": "down", "reason": "설명"}]
    return {"concept": {"id": cid, "name": name, "theme": "환율", "kind": "indicator",
                        "aliases": list(aliases), "edges": edges}}


NONE = {"concept": None}


def fake_create(monkeypatch, *payloads, stop="end_turn"):
    """호출 순서대로 응답을 돌려주는 가짜 create. 호출 인자를 모아 돌려준다."""
    queue, calls = list(payloads), []

    def create(module, **kwargs):
        calls.append({"module": module, **kwargs})
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=json.dumps(queue.pop(0)))])

    monkeypatch.setattr(pr, "create", create)
    return calls


def run(monkeypatch, *payloads):
    calls = fake_create(monkeypatch, *payloads)
    return pr.propose(SOURCE, CONCEPTS, GRAPH), calls


def test_two_matching_extractions_become_candidate(monkeypatch):
    # 이름과 이유 문장은 달라도 id·연결·방향이 같으면 통과
    second = payload(name="달러 환율", edges=[
        {"existing": "rate_hike", "position": "existing_to_new", "force_dir": "down", "reason": "다른 표현"}])
    out, calls = run(monkeypatch, payload(), second)
    assert out.status == "candidate" and out.errors == []
    assert out.proposal.id == "fx_rate"
    assert out.proposal.edges == [("rate_hike", "fx_rate", "down")]   # 기존 → 새 개념 방향으로 풀림
    assert len(calls) == 2 and calls[0]["module"] == "proposals"
    assert calls[0]["messages"] == calls[1]["messages"]               # 같은 자료, 서로의 답은 넘기지 않음


def test_no_proposal_twice(monkeypatch):
    out, _ = run(monkeypatch, NONE, NONE)
    assert out.status == "none" and out.proposal is None


@pytest.mark.parametrize("first, second", [
    (payload(), payload(cid="won_dollar")),                                  # id 가 다름
    (payload(), payload(edges=[{"existing": "rate_hike", "position": "existing_to_new",
                                "force_dir": "up", "reason": ""}])),         # 방향이 다름
    (payload(), payload(edges=[{"existing": "bond_yield", "position": "existing_to_new",
                                "force_dir": "down", "reason": ""}])),       # 잇는 개념이 다름
    (payload(), NONE),                                                       # 한 번만 제안
    (NONE, payload()),
])
def test_different_extractions_are_not_candidates(monkeypatch, first, second):
    out, _ = run(monkeypatch, first, second)
    assert out.status == "mismatch" and "2회 결과가 달라요" in out.errors[0]


@pytest.mark.parametrize("p, message", [
    (payload(cid="bond_yield"), "기존 개념과 겹쳐요"),                 # id
    (payload(name="국채금리"), "국채금리 = bond_yield"),               # 이름 (띄어쓰기 무시)
    (payload(aliases=("금리 올림",)), "금리 올림 = rate_hike"),        # 별칭
    (payload(cid="Bad-Id"), "영문 소문자"),
    (payload(edges=[]), "연결이 없어요"),
    (payload(edges=[
        {"existing": "rate_hike", "position": "existing_to_new", "force_dir": "up", "reason": ""},
        {"existing": "rate_hike", "position": "existing_to_new", "force_dir": "down", "reason": ""},
    ]), "방향이 둘"),
])
def test_rejected_by_code(monkeypatch, p, message):
    out, _ = run(monkeypatch, p, p)
    assert out.status == "rejected"
    assert any(message in e for e in out.errors)


def test_cycle_is_rejected(monkeypatch):
    # bond_yield → 새 개념 → rate_hike 를 이으면 기존 rate_hike → bond_yield 와 순환
    p = payload(edges=[
        {"existing": "bond_yield", "position": "existing_to_new", "force_dir": "up", "reason": ""},
        {"existing": "rate_hike", "position": "new_to_existing", "force_dir": "up", "reason": ""},
    ])
    out, _ = run(monkeypatch, p, p)
    assert out.status == "rejected" and "순환" in out.errors[0]
    assert "fx_rate" not in GRAPH.names                              # 원래 사전은 건드리지 않음


def test_truncated_response_raises(monkeypatch):
    fake_create(monkeypatch, payload(), payload(), stop="max_tokens")
    with pytest.raises(RuntimeError, match="stop_reason=max_tokens"):
        pr.propose(SOURCE, CONCEPTS, GRAPH)


def test_schema_limits_edges_to_dictionary():
    concept, nothing = pr.output_schema(CONCEPTS)["properties"]["concept"]["anyOf"]
    assert nothing == {"type": "null"}                               # 제안 없음을 고를 수 있다
    edge = concept["properties"]["edges"]["items"]
    assert edge["properties"]["existing"]["enum"] == ["rate_hike", "bond_yield"]
    assert edge["properties"]["force_dir"]["enum"] == ["up", "down"]


def test_system_lists_aliases():
    assert "rate_hike | 기준금리 인상 | 금리 | 금리 인상, 금리 올림" in pr.build_system(CONCEPTS)


def test_save_candidate_appends_unverified(monkeypatch, tmp_path):
    out, _ = run(monkeypatch, payload(), payload())
    path = tmp_path / "logs" / "candidates.jsonl"
    pr.save_candidate(out, SOURCE, path)
    pr.save_candidate(out, SOURCE, path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2                                            # 같은 개념이 다시 나오면 쌓인다
    assert rows[0]["id"] == "fx_rate" and rows[0]["verified"] is False
    assert rows[0]["source"]["title"] == SOURCE["title"]


def test_real_dictionary_loads():
    concepts = pr.load_concepts()
    assert len(concepts) == 17 and {"id", "name", "theme", "kind", "aliases"} <= set(concepts[0])
