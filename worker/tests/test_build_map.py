"""개념 지도 전체 잇기·⑤ 저장. DB·실제 모델·실제 API 없이 가짜 임베딩과 가짜 답으로 본다."""
import json

import numpy as np

from concepts import build_map as bm
from concepts import prereq_votes as pv
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
    assert r["counts"] == {"terms": 4, "terms_from_source": 1, "nodes": 2, "merged_nodes": 2, "prereqs": 0}
    assert [(n["id"], n["label"], n["aliases"]) for n in r["nodes"]] == [
        ("c001", "순이익", ["당기순이익"]), ("c002", "주당순이익", ["EPS"])]
    assert r["nodes"][0]["card_ids"] == [1, 2, 3]
    assert r["prereq_stats"] is None and r["prereqs"] == []


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
