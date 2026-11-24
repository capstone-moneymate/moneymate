"""개념 지도 전체 잇기·⑤ 저장. DB·실제 모델·실제 API 없이 가짜 임베딩과 가짜 답으로 본다."""
import json

import numpy as np

from concepts import build_map as bm
from concepts import prereq_votes as pv
from concepts import term_groups as tg_mod
from concepts.concept_map import Materials, Term

# 2차원 길이 1 벡터. 순이익·당기순이익 유사도 0.96, EPS·주당순이익 0.98, 나머지는 멀다
VECS = {
    "순이익": [1.0, 0.0], "당기순이익": [0.96, 0.28],
    "주당순이익": [0.0, 1.0], "EPS": [0.2, 0.98],
}


def encode(texts):
    return np.array([VECS[t] for t in texts], dtype=float)


def materials():
    return Materials([
        Term("순이익", "회사가 번 돈", [1, 2]),
        Term("주당순이익", "순이익 ÷ 주식 수", [1, 2]),
        Term("당기순이익", "", [3]),
        Term("EPS", "", [2], origin="source"),
    ], {})


def test_run_groups_without_prereq():
    r = bm.run(materials(), encode, threshold=0.9)
    assert r["counts"] == {"terms": 4, "terms_from_source": 1, "nodes": 2, "merged_nodes": 2, "prereqs": 0,
                           "confusable_nodes": 0}
    assert r["confusable"] == {}   # 두 묶음 사이 가장 가까운 쌍이 0.47 이라 0.70 아래
    assert [(n["id"], n["label"], n["aliases"]) for n in r["nodes"]] == [
        ("c001", "순이익", ["당기순이익"]), ("c002", "주당순이익", ["EPS"])]
    assert r["nodes"][0]["card_ids"] == [1, 2, 3]
    assert r["prereq_stats"] is None and r["prereqs"] == []


def test_close_but_not_merged_becomes_confusable():
    # 기준 0.97 이면 순이익·당기순이익(0.96)은 따로 남고, 0.70 이상이라 서로 헷갈리는 이웃이 된다
    r = bm.run(materials(), encode, threshold=0.97)
    assert [n["label"] for n in r["nodes"]] == ["순이익", "주당순이익", "당기순이익"]
    assert r["confusable"] == {"순이익": ["당기순이익"], "당기순이익": ["순이익"]}
    assert r["counts"]["confusable_nodes"] == 2 and r["settings"]["confusable_low"] == 0.70


def test_default_threshold_is_090():
    assert bm.tg.DEFAULT_THRESHOLD == 0.90


def test_review_lists_merged_lowest_first():
    r = bm.run(materials(), encode, threshold=0.9)
    assert r["review"] == [
        {"id": "c001", "members": ["순이익", "당기순이익"], "min_sim": 0.96},
        {"id": "c002", "members": ["주당순이익", "EPS"], "min_sim": 0.98},
    ]


def test_run_with_prereq(monkeypatch):
    # 늘 "순이익이 먼저"라고 답하는 가짜. 순서를 바꿔 물어도 같은 뜻
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first" if x.label == "순이익" else "second")
    r = bm.run(materials(), encode, threshold=0.9, prereq=True)
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": 4, "total": 4}]
    assert r["prereq_stats"] == {"pairs": 1, "calls": 4, "edges": 1, "split": 0, "none": 0}
    assert "선수 관계 1개" in bm.summary(r) and "호출 4회" in bm.summary(r)


def test_run_empty():
    r = bm.run(Materials([], {}), encode, prereq=True)
    assert r["counts"]["nodes"] == 0 and r["review"] == []


def test_save_files(tmp_path):
    r = bm.run(materials(), encode, threshold=0.9)
    main, review = bm.save(r, tmp_path)
    assert json.loads(main.read_text(encoding="utf-8"))["counts"]["nodes"] == 2
    lines = review.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == "id\t최저유사도\t묶인 용어\t잘못(O 표시)"
    assert lines[1] == "c001\t0.96\t순이익 | 당기순이익\t"


def test_prereq_cycles_are_broken_and_review_file_written(monkeypatch, tmp_path):
    # 순이익 → 주당순이익 (4표), 주당순이익 → 순이익 (3표) 이 둘 다 나오면 순환: 표가 적은 쪽을 뺀다
    monkeypatch.setattr(pv, "build_prereqs", lambda nodes, pairs: (
        [pv.Prereq(0, 1, 4, 4), pv.Prereq(1, 0, 3, 4)], {"pairs": 1, "calls": 8, "edges": 2, "split": 0, "none": 0}))
    r = bm.run(materials(), encode, threshold=0.97, prereq=True)
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": 4, "total": 4}]
    assert r["prereqs_removed_for_cycles"] == [{"pre_id": "c002", "post_id": "c001", "votes": 3}]
    bm.save(r, tmp_path)
    lines = (tmp_path / "prereq_review.tsv").read_text(encoding="utf-8-sig").splitlines()
    assert lines[1] == "순이익\t주당순이익\t4/4\t" and lines[2] == "주당순이익\t순이익\t3\t순환이라 뺌"


def test_tutor_reads_confusable_from_map():
    from tutor.agent import ConceptMap
    r = bm.run(materials(), encode, threshold=0.97)
    m = ConceptMap.from_build(r)
    assert m.confusable == {"순이익": ["당기순이익"], "당기순이익": ["순이익"]}
    assert ConceptMap.from_build(r, confusable={}).confusable == {}


def test_prereq_review_drop_add_and_merge(monkeypatch):
    # LLM 은 늘 "순이익 → 주당순이익". 검토 파일은 그걸 drop 하고 사람이 "주당순이익 → 당기순이익"을 add (지도용 가짜)
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first" if x.label == "순이익" else "second")
    rows = [pv.PrereqRow("순이익", "주당순이익", "drop", "4/4"), pv.PrereqRow("주당순이익", "당기순이익", "add")]
    r = bm.run(materials(), encode, threshold=0.97, prereq=True, prereq_review=rows)
    # 순이익 → 주당순이익 은 사람이 이미 drop 해서 다시 넣지 않는다. 순이익 → 당기순이익 은 처음 나온 연결이라 빈칸 줄로 더함
    assert r["prereq_stats"]["new_review_rows"] == 1 and rows[2] == pv.PrereqRow("순이익", "당기순이익", "", "4/4")
    assert r["prereqs"] == [{"pre_id": "c002", "post_id": "c003", "votes": pv.HUMAN_VOTES, "total": 4},
                            {"pre_id": "c001", "post_id": "c003", "votes": 4, "total": 4}]
    # LLM 없이 다시 만들어도 같다
    assert bm.run(materials(), encode, threshold=0.97, prereq_review=rows)["prereqs"] == r["prereqs"]


def test_new_llm_edge_becomes_blank_row_and_counts(monkeypatch):
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first" if x.label == "순이익" else "second")
    rows = []
    r = bm.run(materials(), encode, threshold=0.9, prereq=True, prereq_review=rows)
    assert rows == [pv.PrereqRow("순이익", "주당순이익", "", "4/4")]
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": 4, "total": 4}]   # 빈칸은 LLM 표 그대로


def test_review_row_with_unknown_name_is_reported():
    rows = [pv.PrereqRow("순이익", "없는 개념", "keep", "3/4")]
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [] and r["prereq_review_missing"] == [{"pre": "순이익", "post": "없는 개념", "decision": "keep"}]


def test_human_edge_survives_cycle_over_llm_edge():
    rows = [pv.PrereqRow("순이익", "주당순이익", "", "4/4"), pv.PrereqRow("주당순이익", "순이익", "add")]
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs_removed_for_cycles"] == [{"pre_id": "c001", "post_id": "c002", "votes": 4}]


def test_prereq_review_file_roundtrip(tmp_path):
    p = tmp_path / "prereq_review.csv"
    rows = [pv.PrereqRow("매출액", "영업이익", "keep", "4/4", "사람 검토")]
    pv.save_prereq_review(rows, p)
    assert pv.load_prereq_review(p) == rows
    assert pv.load_prereq_review(tmp_path / "없음.csv") == []


def test_review_row_with_old_name_found_by_alias(monkeypatch):
    # 기준 0.9 에서 '당기순이익'은 '순이익' 노드의 별칭. 예전 이름으로 적힌 줄도 같은 연결이고, 같은 LLM 연결을 또 더하지 않는다
    rows = [pv.PrereqRow("당기순이익", "EPS", "keep", "4/4")]
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": pv.HUMAN_VOTES, "total": 4}]
    assert r["prereq_review_missing"] == []
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first" if x.label == "순이익" else "second")
    r = bm.run(materials(), encode, threshold=0.9, prereq=True, prereq_review=rows)
    assert r["prereq_stats"]["new_review_rows"] == 0 and len(rows) == 1


def test_main_with_prereq_and_one_node_still_saves(monkeypatch, tmp_path):
    # 노드가 1개면 ④ 를 안 돌려 prereq_stats 가 None. 그래도 지도 파일은 저장한다 (#219 리뷰)
    import db
    from contextlib import nullcontext
    monkeypatch.setattr(db, "get_conn", lambda: nullcontext(None))
    monkeypatch.setattr(bm, "gather", lambda conn: Materials([Term("순이익", "", [1])], {}))
    monkeypatch.setattr(bm.tg, "load_encoder", lambda model: encode)
    monkeypatch.setattr(bm, "load_review", lambda: [])
    monkeypatch.setattr(pv, "load_prereq_review", lambda: [])
    monkeypatch.setattr(pv, "save_prereq_review", lambda rows: None)
    monkeypatch.setattr(bm.tg, "load_confusable_review", lambda: [])
    monkeypatch.setattr(bm.tg, "save_confusable_review", lambda rows: None)
    monkeypatch.setattr(bm, "OUT_DIR", tmp_path)
    saved = {}
    monkeypatch.setattr(bm, "save", lambda result: saved.setdefault("r", result) and (tmp_path / "a", tmp_path / "b"))
    monkeypatch.setattr("sys.argv", ["build_map", "--prereq"])
    bm.main()
    assert saved["r"]["counts"]["nodes"] == 1 and saved["r"]["prereq_stats"] is None


def test_dropped_pair_stays_dropped_through_alias_row():
    # '당기순이익'은 '순이익' 노드의 별칭. 대표 이름 줄을 drop 했으면 별칭으로 적힌 빈칸 줄이 있어도 빠진다 (#219 리뷰)
    rows = [pv.PrereqRow("순이익", "주당순이익", "drop", "4/4"), pv.PrereqRow("당기순이익", "EPS", "", "3/4")]
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [] and r["prereq_review_conflicts"] == []
    rows.append(pv.PrereqRow("당기순이익", "주당순이익", "keep"))   # 같은 쌍에 drop 과 keep: 빼고 알린다
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [] and r["prereq_review_conflicts"] == [{"pre": "순이익", "post": "주당순이익"}]


def test_human_kept_pair_not_lost_through_weaker_duplicate():
    # A→B 사람 keep(5), 별칭 A'→B 빈칸 3표, B→A 빈칸 4표. 쌍마다 하나로 합쳐서 순환에서는 B→A(4) 만 빠진다 (#219 리뷰)
    rows = [pv.PrereqRow("순이익", "주당순이익", "keep"), pv.PrereqRow("당기순이익", "주당순이익", "", "3/4"),
            pv.PrereqRow("주당순이익", "순이익", "", "4/4")]
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": pv.HUMAN_VOTES, "total": 4}]
    assert r["prereqs_removed_for_cycles"] == [{"pre_id": "c002", "post_id": "c001", "votes": 4}]


def test_alias_rows_merge_to_highest_llm_votes_and_skip_same_node():
    rows = [pv.PrereqRow("당기순이익", "EPS", "", "3/4"), pv.PrereqRow("순이익", "주당순이익", "", "4/4"),
            pv.PrereqRow("순이익", "당기순이익", "", "4/4")]   # 같은 노드끼리는 연결이 아니다
    r = bm.run(materials(), encode, threshold=0.9, prereq_review=rows)
    assert r["prereqs"] == [{"pre_id": "c001", "post_id": "c002", "votes": 4, "total": 4}]


def test_confusable_review_keeps_only_human_kept_pairs():
    # 기준 0.97 이면 순이익·당기순이익(0.96)이 따로 남아 후보 쌍. 검토 파일이 비었으면 빈칸 줄만 생기고 지도에는 안 들어간다
    rows = []
    r = bm.run(materials(), encode, threshold=0.97, confusable_review=rows)
    assert rows == [tg_mod.ConfusableRow("순이익", "당기순이익", "0.960")] and r["confusable_review_new"] == 1
    assert r["confusable"] == {} and r["confusable_pairs"] == [] and r["counts"]["confusable_nodes"] == 0
    rows[0].decision = "keep"
    r = bm.run(materials(), encode, threshold=0.97, confusable_review=rows)
    assert r["confusable"] == {"순이익": ["당기순이익"], "당기순이익": ["순이익"]} and r["confusable_review_new"] == 0
    assert r["confusable_pairs"] == [{"a": "순이익", "b": "당기순이익", "sim": 0.96}]


def test_without_confusable_review_pairs_is_none():
    assert bm.run(materials(), encode, threshold=0.97)["confusable_pairs"] is None
