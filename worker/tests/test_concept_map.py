"""개념 지도 ① 재료 모으기, ② 용어 뽑기. DB 와 실제 API 없이 본다."""
import json
from types import SimpleNamespace

import pytest

from concepts import concept_map as cm
from concepts.concept_map import Materials, Term, collect_terms, save_materials, term_key


def test_term_key_ignores_spaces_and_case():
    assert term_key("주당 순이익") == term_key("주당순이익")
    assert term_key(" eps ") == term_key("EPS")
    assert term_key("EPS") != term_key("주당순이익")  # 뜻이 같은 다른 말은 ③ 임베딩에서 묶는다


def test_collect_merges_same_text_and_keeps_order():
    rows = [
        (1, [{"term": "기준금리", "desc": "중앙은행이 정하는 금리"}, {"term": "EPS", "desc": "주당순이익"}]),
        (2, [{"term": "eps", "desc": "순이익 ÷ 주식 수"}, {"term": "환율", "desc": "두 나라 돈의 교환 비율"}]),
        (3, [{"term": "기준 금리", "desc": "중앙은행이 정하는 금리"}]),
    ]
    terms = collect_terms(rows)
    assert [t.term for t in terms] == ["기준금리", "EPS", "환율"]  # 처음 나온 표기·순서
    rate, eps, fx = terms
    assert rate.card_ids == [1, 3] and rate.descs == []           # 같은 설명은 다시 넣지 않음
    assert eps.card_ids == [1, 2] and eps.descs == ["순이익 ÷ 주식 수"]
    assert fx.card_ids == [2]


def test_collect_skips_empty_and_same_card_twice():
    rows = [
        (1, None),                                   # terms 가 없는 concept 단계
        (2, [{"term": "  ", "desc": "빈 용어"}, {"term": "PER", "desc": ""}]),
        (2, [{"term": "PER", "desc": "주가 ÷ EPS"}]),  # 같은 카드의 다른 concept 단계
    ]
    terms = collect_terms(rows)
    assert len(terms) == 1
    per = terms[0]
    assert per.card_ids == [2]
    assert per.desc == "" and per.descs == ["주가 ÷ EPS"]


def test_save_materials(tmp_path):
    m = Materials([Term("환율", "교환 비율", [2])], {2: ["원/달러 환율 1,500원 돌파"]})
    data = json.loads(save_materials(m, tmp_path).read_text(encoding="utf-8"))
    assert data["terms"][0]["term"] == "환율"
    assert data["sources"] == {"2": ["원/달러 환율 1,500원 돌파"]}


# --- ② 용어 뽑기. 실제 API 는 부르지 않는다 (create 를 가짜로 바꾼다) ---
TITLES = ["한국은행 기준금리 0.25%p 인하", "삼성전자 자기주식 취득 결정"]


def fake_create(monkeypatch, *payloads, stop="end_turn"):
    queue, calls = list(payloads), []

    def create(module, **kwargs):
        calls.append({"module": module, **kwargs})
        return SimpleNamespace(stop_reason=stop,
                               content=[SimpleNamespace(type="text", text=json.dumps({"terms": queue.pop(0)}))])

    monkeypatch.setattr(cm, "create", create)
    return calls


def test_check_keeps_only_terms_in_titles():
    items = [
        {"term": "기준 금리", "desc": "중앙은행이 정하는 금리"},  # 띄어쓰기만 달라도 제목에 있음
        {"term": "자기주식 취득", "desc": "회사가 자기 주식을 사는 것"},
        {"term": "주당순이익", "desc": "지어낸 말"},                # 제목에 없음
        {"term": "0.25", "desc": "숫자"},
        {"term": "", "desc": "빈 값"},
        {"term": "인하", "desc": "이미 있음"},
    ]
    kept, dropped = cm.check_extracted(items, TITLES, known_keys={cm.term_key("인하")})
    assert [k["term"] for k in kept] == ["기준 금리", "자기주식 취득"]
    assert dropped == ["주당순이익: 제목에 없음", "0.25: 숫자", "(빈 값): 빈 용어", "인하: 이미 있음"]


def test_check_drops_long_duplicate_and_over_limit(monkeypatch):
    monkeypatch.setattr(cm, "MAX_EXTRACT", 1)
    items = [{"term": "기준금리", "desc": ""}, {"term": "기준금리", "desc": ""},
             {"term": "삼성전자 자기주식 취득 결정이라는 아주 긴 구절", "desc": ""}, {"term": "자기주식", "desc": ""}]
    kept, dropped = cm.check_extracted(items, TITLES + ["삼성전자 자기주식 취득 결정이라는 아주 긴 구절"], set())
    assert [k["term"] for k in kept] == ["기준금리"]
    assert dropped == ["기준금리: 이미 있음", "삼성전자 자기주식 취득 결정이라는 아주 긴 구절: 너무 김", "자기주식: 상한 초과"]


def test_extract_adds_new_and_links_existing(monkeypatch):
    m = Materials([Term("기준금리", "중앙은행이 정하는 금리", [1]), Term("자사주", "", [2])],
                  {1: ["기준금리 인하"], 2: ["자기주식 취득 결정, 기준금리 영향"]})
    calls = fake_create(monkeypatch,
                        [{"term": "인하", "desc": "낮춤"}],                                       # 카드 1
                        [{"term": "자기주식", "desc": "회사가 가진 자기 주식"}, {"term": "기준금리", "desc": "x"}])  # 카드 2
    stats = cm.extract_terms(m)
    assert stats == {"cards": 2, "added": 2, "linked": 1, "dropped": 0}
    by = {t.term: t for t in m.terms}
    assert by["기준금리"].card_ids == [1, 2]                     # 새로 만들지 않고 카드 2를 더함
    assert by["인하"].origin == "source" and by["자기주식"].card_ids == [2]
    assert calls[0]["module"] == "concept_map" and calls[0]["card_id"] == 1
    assert '"기준금리"' in calls[0]["messages"][0]["content"].split("</known>")[0]   # 이 카드 용어는 known 으로
    assert "자사주" not in calls[0]["messages"][0]["content"]                       # 다른 카드 용어는 안 넘김


def test_extract_skips_cards_without_sources(monkeypatch):
    m = Materials([Term("환율", "", [3])], {})
    calls = fake_create(monkeypatch)
    assert cm.extract_terms(m)["cards"] == 0 and calls == []


def test_extract_raises_on_cut_response(monkeypatch):
    fake_create(monkeypatch, [], stop="max_tokens")
    with pytest.raises(RuntimeError):
        cm.extract_terms(Materials([], {1: TITLES}))
