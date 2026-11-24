"""튜터 에이전트 반복: 도구 실행, 퀴즈에서 멈추고 답으로 이어가기, 상한. 모델 응답은 미리 정한 가짜다."""
from types import SimpleNamespace

import pytest

from tutor import agent as ag
from tutor import quiz as qz
from tutor.mastery import FakeMastery
from tutor.quiz import Quiz

# 순이익 → 주당순이익 ← 유통 주식 수 → 자사주 소각
CMAP = ag.ConceptMap(
    ["순이익", "유통 주식 수", "주당순이익", "자사주 소각", "환율"],
    {"순이익": "회사가 번 돈", "주당순이익": "순이익 ÷ 주식 수"},
    [("순이익", "주당순이익", 4), ("유통 주식 수", "주당순이익", 3), ("유통 주식 수", "자사주 소각", 4)],
    {"주당순이익": ["주당순자산"]},
)
TARGETS = ["주당순이익", "자사주 소각"]


def tool_use(name, **inp):
    inp = {"reason": f"{name} 이유", **inp}
    d = {"type": "tool_use", "id": f"tu_{name}_{len(inp)}", "name": name, "input": inp}
    return SimpleNamespace(**d, to_dict=lambda d=d: d)


def text(t):
    d = {"type": "text", "text": t}
    return SimpleNamespace(**d, to_dict=lambda d=d: d)


def script(monkeypatch, *responses):
    """모델 응답을 순서대로 돌려주는 가짜 create. (stop_reason, [블록]) 목록."""
    queue, calls = list(responses), []

    def create(module, **kw):
        calls.append({"module": module, **kw, "messages": list(kw["messages"])})
        stop, blocks = queue.pop(0)
        return SimpleNamespace(stop_reason=stop, content=blocks)

    monkeypatch.setattr(ag, "create", create)
    return calls


def fake_quiz(monkeypatch):
    def make(s, concept, kind):
        if kind == "사례 분류":
            raise qz.QuizError("만들기 실패")
        return qz.Quiz(kind, concept, {"question": "?", "options": ["a", "b", "c"]}, 0, "해설", 1 / 3)
    monkeypatch.setattr(ag, "make_quiz", make)


def session(p=None):
    return ag.Session("u1", CMAP, TARGETS, FakeMastery({"u1": p or {}}), card="자사주 소각 카드")


def test_concept_map_from_build_and_ancestors():
    result = {"nodes": [{"id": "c001", "label": "A", "desc": "a"}, {"id": "c002", "label": "B", "desc": "b"}],
              "prereqs": [{"pre_id": "c001", "post_id": "c002", "votes": 4, "total": 4},
                          {"pre_id": "c002", "post_id": "c001", "votes": 3, "total": 4}]}  # 순환: 표 3 쪽을 뺀다
    m = ag.ConceptMap.from_build(result)
    assert m.labels == ["A", "B"] and m.edges == [("A", "B", 4)] and m.desc["B"] == "b"
    assert CMAP.ancestors(["주당순이익"]) == ["순이익", "유통 주식 수", "주당순이익"]
    assert CMAP.ancestors(TARGETS) == ["순이익", "유통 주식 수", "주당순이익", "자사주 소각"]  # 환율은 빠진다


def test_ready_tool_by_hand():
    out = ag.tool_ready(session({"순이익": 0.97}))
    # 순이익만 앎 → 유통 주식 수만 준비됨. 두 목표 모두 유통 주식 수를 몰라서 아직
    assert out["ready"] == [{"concept": "유통 주식 수", "p_know": 0.0, "confusable": []}]
    assert out["targets"] == [
        {"concept": "주당순이익", "p_know": 0.0, "state": "선수 개념 먼저", "missing": ["유통 주식 수"]},
        {"concept": "자사주 소각", "p_know": 0.0, "state": "선수 개념 먼저", "missing": ["유통 주식 수"]},
    ]
    out = ag.tool_ready(session({"순이익": 0.97, "유통 주식 수": 0.97, "주당순이익": 0.96}))
    assert [t["state"] for t in out["targets"]] == ["앎", "준비됨"]
    assert [r["concept"] for r in out["ready"]] == ["자사주 소각"]


def test_flow_pauses_on_quiz_and_resumes(monkeypatch):
    fake_quiz(monkeypatch)
    calls = script(monkeypatch,
                   ("tool_use", [tool_use("ready_concepts")]),
                   ("tool_use", [tool_use("ask_quiz", concept="유통 주식 수", kind="용어 뜻")]),
                   ("tool_use", [tool_use("explain", concept="유통 주식 수", style="예시 위주", text="시장에 도는 주식 수예요.")]),
                   ("tool_use", [tool_use("go_main")]))
    s = ag.start(session({"순이익": 0.97}))
    assert s.status == "waiting" and s.quizzes == 1 and len(calls) == 2
    assert s.events[-1]["type"] == "quiz" and s.events[-1]["guess_p"] == pytest.approx(0.333)
    assert "key" not in s.events[-1] and 0 not in s.events[-1]["content"].values()   # 정답은 화면에 안 나간다

    s = ag.answer(s, 1, "확신해요")   # 확신했는데 틀림
    assert s.status == "done" and s.finished_by == "go_main" and len(calls) == 4
    assert s.mastery.get_mastery("u1")["유통 주식 수"] == 0.0
    assert [e["tool"] for e in s.log] == ["ready_concepts", "ask_quiz", "explain", "go_main"]
    assert s.log[1]["reason"] == "ask_quiz 이유" and s.log[1]["result"] == {"correct": False, "confidence": "확신해요"}
    assert [e["type"] for e in s.events] == ["quiz", "graded", "explain", "done"]
    # 답이 tool_result 로 넘어가고, 모델 설정이 맞다
    last_user = calls[2]["messages"][-1]["content"][0]
    assert last_user["tool_use_id"] == "tu_ask_quiz_3" and '"correct": false' in last_user["content"]
    assert calls[0]["model"] == "claude-opus-5-5" and calls[0]["output_config"] == {"effort": "low"}
    assert calls[0]["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert calls[0]["cache_control"] == {"type": "ephemeral"}
    assert calls[0]["system"] == calls[3]["system"] and calls[0]["tools"] == calls[3]["tools"]  # 캐시 앞부분이 그대로


def test_quiz_error_goes_back_to_agent(monkeypatch):
    fake_quiz(monkeypatch)
    calls = script(monkeypatch,
                   ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="사례 분류")]),
                   ("tool_use", [tool_use("go_main")]))
    s = ag.start(session())
    res = calls[1]["messages"][-1]["content"][0]
    assert res["is_error"] and res["content"] == "만들기 실패" and s.finished_by == "go_main" and s.quizzes == 0


def test_explain_banned_is_rejected(monkeypatch):
    calls = script(monkeypatch,
                   ("tool_use", [tool_use("explain", concept="순이익", style="정의 위주", text="지금 매수 추천")]),
                   ("tool_use", [tool_use("go_main")]))
    s = ag.start(session())
    assert calls[1]["messages"][-1]["content"][0]["is_error"]
    assert not any(e["type"] == "explain" for e in s.events)


def test_limits(monkeypatch):
    fake_quiz(monkeypatch)
    script(monkeypatch,
           ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="O/X")]),
           ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="O/X")]))
    one = session()
    one.max_quizzes = 1                      # 상한은 세션마다 (1-5 평가의 6 / 10 비교, #238)
    s = ag.start(one)
    assert '"max_quizzes": 1' in s.messages[0]["content"]
    s = ag.answer(s, 0, "확신해요")
    assert s.finished_by == "quiz_limit" and s.quizzes == 1

    monkeypatch.setattr(ag, "MAX_CALLS", 2)
    script(monkeypatch, *[("tool_use", [tool_use("ready_concepts")])] * 2)
    assert ag.start(session()).finished_by == "call_limit"


def test_text_only_is_nudged_once(monkeypatch):
    calls = script(monkeypatch, ("end_turn", [text("음..")]), ("end_turn", [text("음..")]))
    s = ag.start(session())
    assert s.finished_by == "no_tool" and calls[1]["messages"][-1]["content"] == "도구 하나를 골라 주세요."
    script(monkeypatch, ("refusal", []))
    assert ag.start(session()).status == "error"


def test_answer_without_pending_raises():
    with pytest.raises(RuntimeError):
        ag.answer(session(), 0, "확신해요")


def test_confusable_pair_needs_neighbor():
    with pytest.raises(qz.QuizError, match="이웃이 없어요"):
        ag.make_quiz(session(), "순이익", "헷갈리는 쌍")


# --- #204 리뷰 반영 ---

def test_unexpected_error_ends_session_and_reraises(monkeypatch):
    def boom(module, **kw):
        raise RuntimeError("API 오류")
    monkeypatch.setattr(ag, "create", boom)
    s = session()
    with pytest.raises(RuntimeError, match="API 오류"):
        ag.start(s)
    assert s.status == "error" and s.finished_by == "stop:RuntimeError"
    assert s.events[-1] == {"type": "done", "by": "stop:RuntimeError"}


def test_error_while_making_quiz_also_ends_session(monkeypatch):
    def make(s, concept, kind):
        raise RuntimeError("월 한도")   # QuizError 가 아닌 오류 (BudgetExceeded 같은)
    monkeypatch.setattr(ag, "make_quiz", make)
    script(monkeypatch, ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="O/X")]))
    s = session()
    with pytest.raises(RuntimeError):
        ag.start(s)
    assert s.status == "error" and s.pending is None


def test_demo_wrong_answer_is_never_the_key():
    from tutor.demo import wrong_answer
    for key in ([0, 1, 1, 0], [1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]):   # 사례 분류 (뒤집어도 같은 것 포함)
        q = qz.Quiz("사례 분류", "c", {"baskets": ["a", "b"], "cases": list("abcd")}, key, "", 1 / 16)
        assert not qz.grade(q, wrong_answer(q))
    chips = qz.Quiz("칩 빈칸", "c", {"sentence": "___ ___", "chips": list("abcd")}, [2, 3], "", 1 / 12)
    assert not qz.grade(chips, wrong_answer(chips))
    choice = qz.Quiz("용어 뜻", "c", {"question": "?", "options": ["a", "b", "c"]}, 2, "", 1 / 3)
    assert not qz.grade(choice, wrong_answer(choice))


def test_measure_counts_multiple_tools_as_miss():
    from scripts.measure_tutor_latency import choice_key
    one = tool_use("ask_quiz", concept="순이익", kind="틀린 설명")
    two = [one, tool_use("explain", concept="순이익", style="예시 위주", text="t")]
    assert choice_key([one]) == "ask_quiz:틀린 설명"
    assert choice_key(two) == "(도구 2개)" and choice_key([]) == "(도구 없음)"


def test_quiz_maker_replaces_generation(monkeypatch):
    # 1-5 평가의 퀴즈 은행: quiz_maker 를 주면 Haiku 출제(make_quiz) 대신 그걸 쓴다 (#238)
    monkeypatch.setattr(ag, "make_quiz", lambda *a: pytest.fail("make_quiz 를 부르면 안 된다"))
    script(monkeypatch, ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="용어 뜻")]))
    got = []
    s = session()
    s.quiz_maker = lambda s_, c, k: got.append((c, k)) or Quiz("용어 뜻", c, {"question": "q", "options": ["a", "b", "c"]},
                                                              0, "e", 1 / 3)
    s = ag.start(s)
    assert got == [("순이익", "용어 뜻")] and s.status == "waiting"
