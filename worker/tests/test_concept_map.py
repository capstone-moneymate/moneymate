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


def test_term_key_ignores_parentheses():
    # 실제 카드에서 같은 뜻으로 확인된 쌍 (2026-11-24 사람 검토)
    assert term_key("지수 기여도(%p)") == term_key("지수 기여도")
    assert term_key("%p(퍼센트포인트)") == term_key("%p")
    assert term_key("매출액 대비(%)") == term_key("매출액 대비")
    assert term_key("매출액 대비") != term_key("매출액")      # 괄호가 아닌 말이 붙으면 다른 용어
    assert term_key("(주)") == "(주)"                        # 괄호를 빼면 빈 용어가 되면 그대로


def test_collect_merges_parenthesized_spelling():
    terms = collect_terms([(1, [{"term": "지수 기여도(%p)", "desc": "a"}]), (2, [{"term": "지수 기여도", "desc": "b"}])])
    assert len(terms) == 1 and terms[0].term == "지수 기여도(%p)" and terms[0].card_ids == [1, 2]


def test_check_finds_term_inside_title_parentheses():
    kept, dropped = cm.check_extracted([{"term": "EPS", "desc": "주당순이익"}], ["삼성전자 주당순이익(EPS) 12% 증가"], set())
    assert [k["term"] for k in kept] == ["EPS"] and dropped == []


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
        {"term": "주당순이익", "desc": "지어낸 말"},                # 글에 없음
        {"term": "0.25", "desc": "숫자"},
        {"term": "", "desc": "빈 값"},
        {"term": "인하", "desc": "이미 있음"},
    ]
    kept, dropped = cm.check_extracted(items, TITLES, known_keys={cm.term_key("인하")})
    assert [k["term"] for k in kept] == ["기준 금리", "자기주식 취득"]
    assert dropped == ["주당순이익: 글에 없음", "0.25: 숫자", "(빈 값): 빈 용어", "인하: 이미 있음"]


def test_check_drops_long_duplicate_and_over_limit(monkeypatch):
    monkeypatch.setattr(cm, "MAX_EXTRACT", 1)
    items = [{"term": "기준금리", "desc": ""}, {"term": "기준금리", "desc": ""},
             {"term": "삼성전자 자기주식 취득 결정이라는 아주 긴 구절", "desc": ""}, {"term": "자기주식", "desc": ""}]
    kept, dropped = cm.check_extracted(items, TITLES + ["삼성전자 자기주식 취득 결정이라는 아주 긴 구절"], set())
    assert [k["term"] for k in kept] == ["기준금리"]
    assert dropped == ["기준금리: 이미 있음", "삼성전자 자기주식 취득 결정이라는 아주 긴 구절: 너무 김", "자기주식: 상한 초과"]


def test_extract_adds_new_and_links_existing(monkeypatch):
    m = Materials([Term("기준금리", "중앙은행이 정하는 금리", [1]), Term("자사주", "", [2])], {},
                  texts={1: ["기준금리 인하"], 2: ["자기주식 취득 결정, 기준금리 영향"]})
    calls = fake_create(monkeypatch,
                        [{"term": "인하", "same_as": "", "desc": "낮춤"}],                                   # 카드 1
                        [{"term": "자기주식 취득", "same_as": "", "desc": "회사가 자기 주식을 사는 것"},
                         {"term": "기준금리", "same_as": "", "desc": "x"}])                                  # 카드 2
    stats = cm.extract_terms(m)
    assert stats == {"cards": 2, "added": 2, "linked": 1, "same_as": 0, "same_rejected": 0, "dropped": 0,
                     "candidates": 0, "candidates_same": 0, "dropped_by_review": 0}
    by = {t.term: t for t in m.terms}
    assert by["기준금리"].card_ids == [1, 2]                     # 새로 만들지 않고 카드 2를 더함
    assert by["인하"].origin == "source" and by["자기주식 취득"].card_ids == [2]
    assert calls[0]["module"] == "concept_map" and calls[0]["card_id"] == 1
    first = calls[0]["messages"][0]["content"]
    assert '"자사주"' in first.split("</map>")[0]                          # 지도 전체 용어는 <map> 으로
    assert first.split("<this_card>")[1].split("</this_card>")[0].strip() == '["기준금리"]'  # 이 카드 용어만
    assert '"인하"' in calls[1]["messages"][0]["content"].split("</map>")[0]  # 앞 카드에서 생긴 용어도 다음부터 지도에
    enum = calls[0]["output_config"]["format"]["schema"]["properties"]["terms"]["items"]["properties"]["same_as"]["enum"]
    assert enum == ["", "기준금리", "자사주"]


def test_extract_same_as_links_to_existing_term(monkeypatch):
    m = Materials([Term("자사주 취득", "회사가 자기 주식을 사는 것", [1])], {}, texts={2: ["자기주식 취득 결정"]})
    fake_create(monkeypatch, [{"term": "자기주식 취득", "same_as": "자사주 취득", "desc": "자기 주식을 삼"}])
    stats = cm.extract_terms(m)
    assert stats["same_as"] == 1 and stats["added"] == 0 and len(m.terms) == 1
    assert m.terms[0].card_ids == [1, 2] and m.terms[0].variants == ["자기주식 취득"]


def test_check_same_as_outside_map_is_cleared_and_dup_is_dropped():
    items = [{"term": "자기주식 취득", "same_as": "지어낸 이름", "desc": ""},
             {"term": "자기주식", "same_as": "자사주 취득", "desc": ""}]
    kept, dropped = cm.check_extracted(items, ["자기주식 취득 결정"], {cm.term_key("자사주 취득")}, ["자사주 취득"])
    # 첫째: 지도 밖 이름이라 same_as 를 비우고 새 용어로 / 둘째: 같은 뜻이라고 한 용어가 이 카드에 이미 있어서 뺀다
    assert kept == [{"term": "자기주식 취득", "same_as": "", "desc": ""}]
    assert dropped == ["자기주식: 이미 있음 (같은 뜻)"]


def test_extract_skips_cards_without_text(monkeypatch):
    m = Materials([Term("환율", "", [3])], {})
    calls = fake_create(monkeypatch)
    assert cm.extract_terms(m)["cards"] == 0 and calls == []


def test_extract_raises_on_cut_response(monkeypatch):
    fake_create(monkeypatch, [], stop="max_tokens")
    with pytest.raises(RuntimeError):
        cm.extract_terms(Materials([], {}, texts={1: TITLES}))


def test_slide_texts_keeps_words_not_numbers():
    slides = [{"heading": "기준금리 그대로", "body": "동결은 유지한다는 뜻이에요.", "label": "무슨 일",
               "facts": [{"label": "결정", "value": "기준금리 동결"}, {"label": "발표일", "value": "2026-10-22"}]},
              {"heading": "", "body": "성장주 가치평가에 부담", "facts": None}]
    assert cm.slide_texts("한국은행 기준금리 동결", slides) == [
        "한국은행 기준금리 동결", "기준금리 그대로", "동결은 유지한다는 뜻이에요.", "결정", "발표일", "성장주 가치평가에 부담"]
    assert cm.slide_texts("", None) == []


def test_extract_uses_card_text_not_source_titles(monkeypatch):
    m = Materials([], {1: ["MICROSOFT CORP 8-K Item 2.02"]}, texts={1: ["영업이익이 늘었어요"]})
    calls = fake_create(monkeypatch, [{"term": "영업이익", "desc": "본업으로 번 돈"}])
    assert cm.extract_terms(m)["added"] == 1
    assert "영업이익이 늘었어요" in calls[0]["messages"][0]["content"] and "8-K" not in calls[0]["messages"][0]["content"]


def test_extract_same_as_rejected_by_check_becomes_new_term(monkeypatch):
    m = Materials([Term("자사주 취득", "", [1])], {}, texts={2: ["자기주식을 보유하고 있다"]})
    fake_create(monkeypatch, [{"term": "자기주식", "same_as": "자사주 취득", "desc": "회사가 가진 자기 주식"}])
    stats = cm.extract_terms(m, same_check=lambda a, b: False)   # 임베딩이 같다고 하지 않음
    assert stats["same_rejected"] == 1 and stats["same_as"] == 0 and stats["added"] == 1
    assert [t.term for t in m.terms] == ["자사주 취득", "자기주식"] and m.terms[0].variants == []


# --- ② 사람 검토 (term_review.csv) ---

from concepts.concept_map import ReviewRow, apply_review, load_review, save_review


def test_review_file_roundtrip(tmp_path):
    rows = [ReviewRow("금융통화위원회", "keep", "", "금리를 정하는 곳"), ReviewRow("마감", "drop", note="일반 단어")]
    path = save_review(rows, tmp_path / "r.csv")
    assert load_review(path) == rows
    assert load_review(tmp_path / "없음.csv") == []


def test_apply_review_keep_same_and_grounding():
    m = Materials([Term("자사주 취득", "", [1])], {},
                  texts={1: ["자사주 취득"], 2: ["자기주식 취득 결정"], 3: ["금융통화위원회가 금리 동결"], 4: ["마감"]})
    rows = [ReviewRow("금융통화위원회", "keep", desc="금리를 정하는 곳"),
            ReviewRow("자기주식 취득", "same", "자사주 취득"),
            ReviewRow("마감", "drop"), ReviewRow("공시", ""), ReviewRow("주주가치", "same", "지도에 없는 이름")]
    stats = apply_review(m, rows)
    assert stats == {"keep": 1, "same": 1, "merged": 0, "missing_target": 1}
    by = {t.term: t for t in m.terms}
    assert by["금융통화위원회"].card_ids == [3] and by["금융통화위원회"].origin == "source"   # 글에 나온 카드에 코드가 잇는다
    assert by["자사주 취득"].variants == ["자기주식 취득"] and by["자사주 취득"].card_ids == [1, 2]
    assert "마감" not in by and "공시" not in by
    apply_review(m, rows)   # 두 번 불러도 같다
    assert len(m.terms) == 2 and by["자사주 취득"].variants == ["자기주식 취득"]


def test_extract_with_review_only_adds_candidates(monkeypatch):
    m = Materials([Term("자사주 취득", "", [1])], {}, texts={2: ["자기주식 취득 결정, 공시일 거래량, 마감"]})
    review = [ReviewRow("마감", "drop")]
    fake_create(monkeypatch, [{"term": "자기주식 취득", "same_as": "자사주 취득", "desc": "a"},
                              {"term": "공시일 거래량", "same_as": "", "desc": "b"},
                              {"term": "마감", "same_as": "", "desc": "c"}])
    s = cm.extract_terms(m, same_check=lambda a, b: True, review=review)
    assert s["candidates"] == 2 and s["candidates_same"] == 1 and s["dropped_by_review"] == 1 and s["added"] == 0
    assert [(r.term, r.decision, r.same_as) for r in review] == [
        ("마감", "drop", ""), ("자기주식 취득", "same", "자사주 취득"), ("공시일 거래량", "", "")]
    assert [t.term for t in m.terms] == ["자사주 취득"]              # 새 용어는 지도에 안 들어간다 (사람이 볼 때까지)
    assert m.terms[0].variants == ["자기주식 취득"] and 2 in m.terms[0].card_ids   # 두 신호 통과한 같은 뜻은 바로


def test_extract_with_review_same_rejected_stays_blank(monkeypatch):
    m = Materials([Term("자사주 취득", "", [1])], {}, texts={2: ["자기주식을 보유"]})
    review = []
    fake_create(monkeypatch, [{"term": "자기주식", "same_as": "자사주 취득", "desc": "a"}])
    s = cm.extract_terms(m, same_check=lambda a, b: False, review=review)
    assert s["same_rejected"] == 1 and [(r.term, r.decision) for r in review] == [("자기주식", "")]
    assert m.terms[0].variants == []


def test_check_same_as_on_card_needs_same_check_to_drop():
    # 카드에 '자사주 취득'이 이미 있고 LLM 이 '자기주식 = 자사주 취득'이라고 하면:
    # same_check 가 거절하면 다른 용어라 후보로 남기고, 받아들이면 같은 뜻 중복이라 뺀다 (#219 리뷰)
    items = [{"term": "자기주식", "same_as": "자사주 취득", "desc": "가진 주식"}]
    texts, known, names = ["자기주식을 자사주 취득으로 늘렸다"], {term_key("자사주 취득")}, ["자사주 취득"]
    kept, dropped = cm.check_extracted(items, texts, known, names, same_check=lambda a, b: False)
    assert [k["term"] for k in kept] == ["자기주식"] and dropped == []
    kept, dropped = cm.check_extracted(items, texts, known, names, same_check=lambda a, b: True)
    assert kept == [] and dropped == ["자기주식: 이미 있음 (같은 뜻)"]
    kept, dropped = cm.check_extracted(items, texts, known, names)   # same_check 없으면 전처럼 뺀다
    assert kept == [] and dropped == ["자기주식: 이미 있음 (같은 뜻)"]


def test_apply_review_same_before_its_keep_row():
    # same 줄이 그 대상 keep 줄보다 앞에 있어도 한 번에 별칭과 카드가 들어간다 (#219 리뷰)
    m = Materials([], {}, texts={1: ["금융통화위원회"], 2: ["금통위 회의"]})
    rows = [ReviewRow("금통위", "same", "금융통화위원회"), ReviewRow("금융통화위원회", "keep")]
    assert apply_review(m, rows) == {"keep": 1, "same": 1, "merged": 0, "missing_target": 0}
    assert m.terms[0].variants == ["금통위"] and m.terms[0].card_ids == [1, 2]


def test_apply_review_same_merges_term_already_on_map():
    # #262: 카드 concept 단계에서 온 용어끼리도 same 으로 합친다 (%p → 지수 기여도(%p)).
    # 이름 바꾸기는 새 이름 keep + 옛 용어 same (매출액 대비 → 매출액 대비 계약 비율)
    m = Materials([Term("%p", "기여도", [6, 26], variants=["%p(퍼센트포인트)"]), Term("지수 기여도(%p)", "비중×등락률", [8]),
                   Term("매출액 대비", "계약금액 ÷ 매출", [9, 27])], {}, texts={})
    rows = [ReviewRow("%p", "same", "지수 기여도(%p)"),
            ReviewRow("매출액 대비", "same", "매출액 대비 계약 비율"),
            ReviewRow("매출액 대비 계약 비율", "keep", desc="계약금액이 매출액의 몇 %인지")]
    assert apply_review(m, rows) == {"keep": 1, "same": 2, "merged": 2, "missing_target": 0}
    by = {t.term: t for t in m.terms}
    assert sorted(by) == ["매출액 대비 계약 비율", "지수 기여도(%p)"]                  # 따로 있던 용어는 없어진다
    assert by["지수 기여도(%p)"].variants == ["%p", "%p(퍼센트포인트)"] and by["지수 기여도(%p)"].card_ids == [6, 8, 26]
    assert by["매출액 대비 계약 비율"].variants == ["매출액 대비"] and by["매출액 대비 계약 비율"].card_ids == [9, 27]
    assert by["매출액 대비 계약 비율"].desc == "계약금액이 매출액의 몇 %인지"
    apply_review(m, rows)   # 두 번 불러도 같다
    assert len(m.terms) == 2 and by["지수 기여도(%p)"].variants == ["%p", "%p(퍼센트포인트)"]
