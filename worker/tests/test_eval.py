"""1-5 가상 학습자 평가 (#238). 실제 API·DB 없이 손으로 만든 퀴즈 은행으로 본다."""
import random
from dataclasses import asdict

import pytest

from eval import bank as bk
from eval import run as rn
from eval import teachers as te
from eval.learner import Learner, prereq_of, profiles, random_answer
from tutor import agent as ag
from tutor.quiz import Quiz

# 개념 3개: 가 → 나 → 다 (다 가 목표)
EDGES = [("가", "나", 4), ("나", "다", 4)]
SCOPE, TARGETS = ["가", "나", "다"], ["다"]


def choice(concept, key=0):
    return Quiz("용어 뜻", concept, {"question": "?", "options": ["a", "b", "c"]}, key, "e", 1 / 3)


def cases(concept):
    return Quiz("사례 분류", concept, {"baskets": ["해당", "아님"], "cases": ["1", "2", "3", "4"]}, [0, 1, 0, 1], "e", 1 / 16)


CARD_BANK = {
    "targets": TARGETS, "scope": SCOPE,
    "teach": {f"{c}|{k}": [asdict(q(c))] for c in SCOPE for k, q in (("용어 뜻", choice), ("사례 분류", cases))},
    "test": {"다": [asdict(choice("다")), asdict(cases("다"))]},
}


def learner(known=(), wrong=(), effect=1.0, p_learn=1.0, slip=0.0, seed=0, conf_noise=None):
    return Learner("t", set(known), set(wrong), prereq_of(EDGES), p_learn=p_learn, prereq_effect=effect, slip=slip,
                   conf_noise=conf_noise, rng=random.Random(seed))


# --- 학습자 ---

def test_respond_by_hidden_state():
    lr = learner(known={"가"}, wrong={"나"}, conf_noise=0.0)
    assert lr.respond(choice("가", 2)) == (2, "확신해요")          # 앎: 정답, 확신
    ans, conf = lr.respond(choice("나", 2))
    assert ans != 2 and conf == "확신해요"                         # 오개념: 확신하고 틀림
    assert lr.respond(choice("다"))[1] == "애매해요"               # 모름: 찍기


def test_confidence_off_by_default_and_noise_flips():
    assert learner(known={"가"}).respond(choice("가"))[1] is None   # 본 비교: 확신을 내지 않는다
    lr = learner(known={"가"}, conf_noise=1.0)
    assert lr.respond(choice("가"))[1] == "애매해요" and lr.respond(choice("다"))[1] == "확신해요"   # 늘 반대
    noisy = learner(known={"가"}, conf_noise=0.4, seed=3)
    flips = sum(noisy.respond(choice("가"))[1] == "애매해요" for _ in range(2000))
    assert abs(flips / 2000 - 0.4) < 0.04


def test_guessing_matches_guess_p():
    rng = random.Random(0)
    q = choice("다")
    hits = sum(random_answer(q, rng) == q.key for _ in range(3000))
    assert abs(hits / 3000 - 1 / 3) < 0.03
    c = cases("다")
    assert abs(sum(random_answer(c, rng) == c.key for _ in range(3000)) / 3000 - 1 / 16) < 0.02


def test_slip():
    lr = learner(known={"가"}, slip=1.0)
    assert lr.respond(choice("가"))[0] != 0


def test_prereq_effect_blocks_learning():
    # 선수 개념 '나' 를 모르면: 효과 0 → 못 배움, 효과 1 → 배움 (p_learn 1.0)
    assert not learner(known={"가"}, effect=0.0).study("다", "explain")
    assert learner(known={"가"}, effect=1.0).study("다", "explain")
    assert learner(known={"가", "나"}, effect=0.0).study("다", "explain")   # 선수 개념을 알면 효과와 상관없다
    lr = learner(wrong={"가"})
    assert lr.study("가", "feedback") and "가" not in lr.wrong            # 오개념도 배우면 고쳐진다
    assert learner(known={"가"}).learn_chance("나") == 1.0 and learner(effect=0.5, p_learn=0.3).learn_chance("나") == 0.15


def test_profiles():
    p = profiles(SCOPE, TARGETS, EDGES)
    assert p["처음 배움"]["known"] == set() and p["기초만 앎"]["known"] == {"가"}
    assert p["거의 앎"]["known"] == {"가", "나"} and p["잘못 앎"] == {"known": {"가"}, "wrong": {"다"}}


# --- 교사 ---

def test_mem_mastery_blind():
    m = te.MemMastery(SCOPE)
    assert m.answer("u", choice("가"), 0, True, None) > 0.3
    blind = te.MemMastery(SCOPE, blind=True)
    assert blind.answer("u", choice("가"), 0, True, None) == pytest.approx(0.3)
    assert blind.get_mastery()["가"] == pytest.approx(0.3) and blind.p["가"] > 0.3   # 갱신은 하지만 보여 주지 않는다


def test_fixed_goes_in_map_order_and_explains_on_wrong():
    lr = learner(effect=0.0, p_learn=0.0)
    ep = te.fixed(SCOPE, TARGETS, lr, bk.Draw(CARD_BANK, random.Random(0)), te.MemMastery(SCOPE), cap=4)
    assert [h["concept"] for h in ep.history] == ["가", "나", "다", "가"] and ep.quizzes == 4
    assert ep.explains == sum(not h["correct"] for h in ep.history) and ep.mastered_at is None


def test_rules_follows_ready_and_lowest_and_stops():
    # 다 아는 학습자: 가 → 나 → 다 순서(선수 관계)로, 알 확률이 0.95 를 넘으면 다음으로. 목표가 0.95 넘으면 끝
    lr = learner(known=set(SCOPE))
    ep = te.rules(SCOPE, TARGETS, EDGES, lr, bk.Draw(CARD_BANK, random.Random(0)), te.MemMastery(SCOPE), cap=30)
    order = [h["concept"] for h in ep.history]
    assert order[0] == "가" and order.index("나") > order.index("가") and order.index("다") > order.index("나")
    assert ep.finished_by == "all_known" and ep.mastered_at == 0
    assert {h["kind"] for h in ep.history} >= {"용어 뜻", "사례 분류"}      # 알 확률이 오르면 사례 분류로


def test_rule_kind():
    assert [te.rule_kind(p) for p in (0.3, 0.6, 0.9)] == ["용어 뜻", "사례 분류", "칩 빈칸"]


def test_mastered_at_counts_quizzes_until_hidden_state_knows_targets():
    lr = learner(known={"가", "나"}, p_learn=1.0)            # 다 를 처음 해설에서 배운다
    ep = te.fixed(["다"], TARGETS, lr, bk.Draw(CARD_BANK, random.Random(0)), te.MemMastery(SCOPE), cap=3)
    assert ep.mastered_at == 1


def test_agent_loop_feeds_learner(monkeypatch):
    # 가짜 에이전트: 설명 → 퀴즈 → 끝. 설명을 들으면 배우고, 답과 확신을 넘긴다
    sent = []

    def start(s):
        s.events.append({"type": "explain", "concept": "다"})
        s.pending, s.status = ("t", choice("다")), "waiting"
        return s

    def answer(s, ans, conf):
        sent.append((ans, conf))
        s.mastery.answer("sim", s.pending[1], ans, ans == 0, conf)
        s.pending, s.status, s.finished_by = None, "done", "go_main"
        return s

    monkeypatch.setattr(ag, "start", start)
    monkeypatch.setattr(ag, "answer", answer)
    cmap = ag.ConceptMap(SCOPE, {}, EDGES)
    lr = learner(known={"가", "나"}, p_learn=1.0)
    ep, s = te.agent(cmap, TARGETS, lr, bk.Draw(CARD_BANK, random.Random(0)), te.MemMastery(SCOPE), cap=6)
    assert ep.explains == 1 and ep.mastered_at == 0 and ep.quizzes == 1 and sent == [(0, None)]   # 확신 없음(기본)
    assert s.max_quizzes == 6 and ep.finished_by == "go_main"


def test_final_test_does_not_teach_and_has_own_rng():
    lr = learner(known=set(), p_learn=1.0, seed=5)
    before = lr.rng.getstate()
    right, total = te.final_test(CARD_BANK["test"], TARGETS, lr, random.Random(9))
    assert total == 2 and lr.known == set() and lr.rng.getstate() == before


def test_bank_draw_cycles_and_missing_kind():
    cb = {"teach": {"가|용어 뜻": [asdict(choice("가", 0)), asdict(choice("가", 1))]}}
    d = bk.Draw(cb, random.Random(0))
    keys = [d(None, "가", "용어 뜻").key for _ in range(4)]
    assert sorted(keys[:2]) == [0, 1] and keys[2:] == keys[:2]
    with pytest.raises(Exception, match="퀴즈가 없어요"):
        d(None, "가", "O/X")


# --- 실행·요약 ---

def test_run_one_same_seed_same_learner_across_conditions():
    cmap = ag.ConceptMap(SCOPE, {}, EDGES)
    c = rn.cell("main", "fixed", 0.5)
    a = rn.run_one(cmap, CARD_BANK, 1, "처음 배움", 0, c)
    b = rn.run_one(cmap, CARD_BANK, 1, "처음 배움", 0, c)
    assert a["history"] == b["history"] and a["test_right"] == b["test_right"]   # 다시 돌려도 같다 (재현)
    assert a["n_targets"] == 1 and a["test_total"] == 2 and a["quizzes"] == 6 and a["bkt"] == "0.3/0.1/0.1"


def test_run_one_bkt_params_and_learner_slip():
    from learner import bkt
    cmap = ag.ConceptMap(SCOPE, {}, EDGES)
    r = rn.run_one(cmap, CARD_BANK, 1, "처음 배움", 0, rn.cell("main", "fixed", 0.5, prior=False),
                   bkt.Params(p_init=0.25, p_learn=0.1, p_slip=0.1))
    assert r["bkt"] == "0.25/0.1/0.1" and set(r["start_p"].values()) == {0.25}   # BKT 값을 바꿔 돌릴 수 있다
    s = rn.run_one(cmap, CARD_BANK, 1, "거의 앎", 0, rn.cell("slip", "fixed", 0.5, slip=0.3))
    assert s["slip"] == 0.3 and rn.key(s) != rn.key({**s, "slip": 0.1})
    assert rn.parse_bkt("0.25,0.2,0.1") == bkt.Params(p_init=0.25, p_learn=0.2, p_slip=0.1) and rn.parse_bkt(None) == bkt.DEFAULT


def test_summarize_by_hand():
    c = rn.cell("main", "rules", 0.5)
    rows = [{**c, "bkt": "0.3/0.1/0.1", "inputs": "abc", "mastered_at": m, "targets_known": k, "n_targets": 2,
             "test_right": r, "test_total": 4, "quizzes": q} for m, k, r, q in ((3, 2, 4, 3), (None, 1, 2, 6))]
    t = rn.summarize(rows)[0]
    assert t == {**c, "bkt": "0.3/0.1/0.1", "inputs": "abc", "n": 2, "test_acc": 0.75, "targets_known": 0.75,
                 "mastered_rate": 0.5, "quizzes": 4.5, "mastered_at": 3}


def test_summarize_empty_test_is_none_and_inputs_split(tmp_path):
    c = rn.cell("main", "rules", 0.5)
    base = {**c, "bkt": "0.3/0.1/0.1", "mastered_at": None, "targets_known": 0, "n_targets": 1, "test_right": 0,
            "test_total": 0, "quizzes": 6}
    rows = [base | {"inputs": "a"}, base | {"inputs": "b"}]
    ts = rn.summarize(rows)
    assert len(ts) == 2 and all(t["test_acc"] is None for t in ts)   # 시험이 없으면 0% 가 아니라 없음, 지문이 다르면 따로
    assert "| 1 | - |" in rn.report(rows, tmp_path).read_text(encoding="utf-8")


def test_grid_counts():
    g = rn.grid()
    agent_cells = [x for x in g if x["condition"].startswith("agent")]
    assert len(agent_cells) == 8 and all(x["prior"] for x in agent_cells)   # 8칸 × 16 = 128 세션
    assert all(x["conf_noise"] is None for x in g if x["setting"] != "conf")   # 확신은 conf 설정에서만
    assert {x["conf_noise"] for x in g if x["setting"] == "conf"} == {0.0, 0.4}
    assert rn.cell("ablation", "agent_no_bkt", 0.5) in g and rn.cell("cap10", "agent", 0.5, cap=10) in g
    assert rn.cell("main", "rules", 0.5, prior=False) in g
    assert {x["slip"] for x in g if x["setting"] == "slip"} == {0.05, 0.2, 0.3}
    assert not any(x["setting"] in ("sens", "slip") and x["condition"].startswith("agent") for x in g)


def test_old_rows_are_skipped(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text('{"setting": "main"}\n' + __import__("json").dumps({**rn.cell("main", "fixed", 0.5), "bkt": "0.3/0.1/0.1",
                 "inputs": "abc", "card": 1, "profile": "처음 배움", "seed": 0}) + "\n", encoding="utf-8")
    assert len(rn.load_rows(p)) == 1   # 확신·BKT 값·입력 지문 기록 전의 옛 줄은 버린다


def test_partial_last_line_is_moved_aside(tmp_path):
    import json
    import pytest
    good = json.dumps({**rn.cell("main", "fixed", 0.5), "bkt": "0.3/0.1/0.1", "inputs": "abc", "card": 1,
                       "profile": "처음 배움", "seed": 0})
    p = tmp_path / "r.jsonl"
    p.write_text(good + "\n" + '{"setting": "ma', encoding="utf-8")   # 쓰다가 끊김
    assert len(rn.load_rows(p)) == 1
    assert p.read_text(encoding="utf-8") == good + "\n"               # 줄바꿈이 맞춰져 다음 줄을 이어 쓸 수 있다
    assert (tmp_path / "r.jsonl.bad").read_text(encoding="utf-8") == '{"setting": "ma\n'
    p.write_text('{"broken\n' + good + "\n", encoding="utf-8")          # 중간 줄이 깨진 건 끊김이 아니다
    with pytest.raises(ValueError):
        rn.load_rows(p)


def test_fingerprint_changes_with_bank_or_map():
    cmap = ag.ConceptMap(SCOPE, {}, EDGES)
    a = rn.fingerprint({"cards": {"1": CARD_BANK}}, cmap)
    assert a == rn.fingerprint({"cards": {"1": CARD_BANK}}, ag.ConceptMap(SCOPE, {}, EDGES))
    assert a != rn.fingerprint({"cards": {}}, cmap) and a != rn.fingerprint({"cards": {"1": CARD_BANK}},
                                                                            ag.ConceptMap(SCOPE, {}, EDGES[:1]))


def test_fixed_stops_when_bank_has_no_term_quiz():
    import pytest
    from tutor import quiz as qz
    bank = {"targets": TARGETS, "teach": {k: v for k, v in CARD_BANK["teach"].items() if "용어 뜻" not in k},
            "test": CARD_BANK["test"]}
    with pytest.raises(qz.QuizError):   # 끝없이 돌지 않고 멈춘다
        te.fixed(SCOPE, TARGETS, learner(), bk.Draw(bank, random.Random(0)), te.MemMastery(SCOPE), cap=6)


def test_test_quiz_differs_from_teach():
    a = {"kind": "용어 뜻", "concept": "가", "content": {"q": "가?", "options": ["x", "y"]}, "key": 0}
    b = {**a, "content": {"q": "가?", "options": ["y", "x"]}}             # 보기 순서만 다름 → 같은 문제
    c = {**a, "content": {"q": "가는?", "options": ["x", "y"]}}
    assert bk.question(a) == bk.question(b) != bk.question(c)
    bank = {"cards": {"1": {"teach": {"가|용어 뜻": [a]}, "test": {"가": [b, c, c]}}}}
    assert bk.overlaps(bank) == [("1", "가", 0), ("1", "가", 2)]


def test_prior_record_same_for_all_conditions_and_does_not_teach():
    # 거의 앎(가·나 앎): 기록 뒤 아는 개념은 알 확률이 오르고 모르는 다 는 낮다. 학습자 상태는 그대로, 씨앗이 같으면 기록도 같다
    recs = []
    for _ in range(2):
        lr = learner(known={"가", "나"}, slip=0.0, p_learn=1.0)
        m = te.MemMastery(SCOPE)
        bank2 = {"teach": {f"{c}|용어 뜻": [asdict(choice(c)), asdict(choice(c, 1))] for c in SCOPE}}
        recs.append(te.prior_record(bank2, SCOPE, lr, m, random.Random(7)))
        assert lr.known == {"가", "나"} and m.p["가"] > 0.8 and m.p["다"] < m.p["가"]
    assert recs[0] == recs[1] and len(recs[0]) == 6


def test_run_one_prior_start_p():
    cmap = ag.ConceptMap(SCOPE, {}, EDGES)
    warm = rn.run_one(cmap, CARD_BANK, 1, "거의 앎", 0, rn.cell("main", "fixed", 0.5, prior=True))
    cold = rn.run_one(cmap, CARD_BANK, 1, "거의 앎", 0, rn.cell("main", "fixed", 0.5, prior=False))
    assert cold["start_p"] == {c: 0.3 for c in SCOPE} and "prior_record" not in cold
    assert warm["start_p"]["가"] > 0.3 and len(warm["prior_record"]) == 3   # 은행에 개념마다 용어 뜻 1개뿐
