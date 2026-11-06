"""scripts/judge_batch.py 테스트. Claude·DB 는 부르지 않는다 (규칙 채점 + 가짜 step 로더)."""
import csv
import json

from scripts import judge_batch

CHAIN = [
    {"name": "기준금리 동결", "aliases": ["동결"]},
    {"name": "예대금리차", "aliases": ["이자 마진"]},
    {"name": "은행 실적", "aliases": ["은행 이익"]},
]
FACTS = [
    {"text": "한은 기준금리 3.00% 동결", "keywords": ["3.00%", "3%"]},
    {"text": "4회 연속 동결", "keywords": ["4회 연속", "네 번 연속"]},
]
COUNTER = [{"name": "경기 둔화", "aliases": ["연체"]}]
ANSWER = ("기준금리가 3%로 4회 연속 동결됐기 때문에 예대금리차가 유지되고, 그래서 은행 실적이 좋아질 것 같다. "
          "하지만 경기 둔화로 연체가 늘면 은행 이익이 줄 수 있다.")


def inline_row(id_, answer):
    return {"id": id_, "answer": answer, "key_facts": json.dumps(FACTS, ensure_ascii=False),
            "chain": json.dumps(CHAIN, ensure_ascii=False), "counter": json.dumps(COUNTER, ensure_ascii=False)}


def test_cli_rule_only_inline_json(tmp_path):
    src, dst = tmp_path / "answers.csv", tmp_path / "scores.csv"
    with src.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "answer", "key_facts", "chain", "counter"])
        w.writeheader()
        w.writerow(inline_row("a1", ANSWER))
        w.writerow(inline_row("a2", "금리가 동결돼서 은행 실적이 좋아질 것 같다."))
    assert judge_batch.main([str(src), str(dst), "--rule-only"]) == 0

    rows = list(csv.DictReader(dst.open(encoding="utf-8-sig")))
    assert list(rows[0]) == judge_batch.OUT_FIELDS
    # 손계산: a1 = 2·3·3 -> 8 -> 89 / a2 = 0·2·0 -> 2 -> 22
    assert [(r["id"], r["evidence"], r["reasoning"], r["rebuttal"], r["score"]) for r in rows] == [
        ("a1", "2", "3", "3", "89"), ("a2", "0", "2", "0", "22")]
    assert all(r["grader"] == "rule" for r in rows)


def test_step_id_uses_loader():
    seen = []

    def loader(step_id):
        seen.append(step_id)
        return {"card_id": 5, "key_facts": FACTS, "chain": CHAIN, "counter": COUNTER}

    out = list(judge_batch.grade_rows([{"id": "s1", "answer": ANSWER, "step_id": "42"}],
                                      judge_batch._rule_grade, loader))
    assert seen == [42]
    assert out[0]["score"] == 89


def test_bad_row_is_recorded_and_continues():
    rows = [{"id": "bad", "answer": ANSWER, "chain": "{not json"}, inline_row("ok", ANSWER)]
    out = list(judge_batch.grade_rows(rows, judge_batch._rule_grade, lambda _: {}))
    assert "score" not in out[0] and out[0]["error"].startswith("JSONDecodeError")
    assert out[1]["score"] == 89
