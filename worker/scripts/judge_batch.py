"""판단 근거 답안 여러 개를 한 번에 채점해 CSV 로 쓴다 (A, 8주차 κ 확인용).

사용 예 (worker 폴더에서):
    python -m scripts.judge_batch answers.csv scores.csv            # Claude 채점 (실패한 답안만 규칙 채점)
    python -m scripts.judge_batch answers.csv scores.csv --rule-only # 규칙 채점만 (비용 0, 비교용)

입력 CSV (UTF-8, 첫 줄은 열 이름). 한 줄에 답안 1개.
- id: 답안 구분용 (아무 문자열). 출력에 그대로 붙는다
- answer: 근거 문장
- 채점 재료는 둘 중 하나
  a) step_id: DB 의 판단해보기 단계 id. 카드의 key_facts 와 steps.answer 의 chain·counter(개념 id)를 DB 에서 읽는다
  b) key_facts, chain, counter: JSON 문자열 열 (judge_api /judge 요청과 같은 형식). DB 없이 돌릴 때
- card_id: (선택) b) 방식일 때 llm_cost_log 비용 집계용

출력 CSV (UTF-8 BOM, 엑셀에서 바로 열림)
id, evidence, reasoning, rebuttal, total, score, grader, reasoning_reason, rebuttal_reason, error

C 의 κ 계산은 evidence·reasoning·rebuttal 열을 사람 합의 점수와 기준별로 비교하면 된다.
"""
import argparse
import csv
import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

OUT_FIELDS = ["id", "evidence", "reasoning", "rebuttal", "total", "score", "grader",
              "reasoning_reason", "rebuttal_reason", "error"]


def load_step_context(step_id: int) -> dict:
    """DB 에서 판단 단계의 채점 재료를 읽어 judge.grade 인자 형식으로 돌려준다."""
    from db import get_conn

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT c.id, c.key_facts, s.answer
            FROM steps s JOIN cards c ON c.id = s.card_id
            WHERE s.id = %s AND s.kind = 'judgement'
            """,
            (step_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"판단해보기 단계가 아니거나 없는 step_id 예요: {step_id}")
        card_id, key_facts, answer = row
        answer = answer or {}
        ids = [*answer.get("chain", []), *answer.get("counter", [])]
        names = {
            cid: {"name": name, "aliases": list(aliases or [])}
            for cid, name, aliases in conn.execute(
                "SELECT id, name, aliases FROM concepts WHERE id = ANY(%s)", (ids,)
            ).fetchall()
        }
    missing = [i for i in ids if i not in names]
    if missing:
        raise ValueError(f"concepts 에 없는 개념 id 예요: {missing}")
    return {
        "card_id": card_id,
        "key_facts": key_facts or [],
        "chain": [names[i] for i in answer.get("chain", [])],
        "counter": [names[i] for i in answer.get("counter", [])],
    }


def row_context(row: dict, step_loader: Callable[[int], dict]) -> dict:
    if (row.get("step_id") or "").strip():
        return step_loader(int(row["step_id"]))
    card_id = (row.get("card_id") or "").strip()
    return {
        "card_id": int(card_id) if card_id else None,
        "key_facts": json.loads(row.get("key_facts") or "[]"),
        "chain": json.loads(row.get("chain") or "[]"),
        "counter": json.loads(row.get("counter") or "[]"),
    }


def grade_rows(rows: Iterable[dict], grade_fn: Callable, step_loader: Callable[[int], dict] = load_step_context):
    """답안 줄마다 채점 결과 줄을 낸다. 한 줄이 실패해도 멈추지 않고 error 열에 남긴다."""
    for row in rows:
        out = {"id": row.get("id", "")}
        try:
            ctx = row_context(row, step_loader)
            r = grade_fn(row["answer"], ctx["key_facts"], ctx["chain"], ctx["counter"], card_id=ctx["card_id"])
            out.update(r.rubric, total=r.total, score=r.score, grader=getattr(r, "grader", "rule"),
                       error=getattr(r, "error", None) or "")
            reasons = getattr(r, "reasons", None) or {}
            out.update(reasoning_reason=reasons.get("reasoning", ""), rebuttal_reason=reasons.get("rebuttal", ""))
        except Exception as e:  # noqa: BLE001 - 입력 줄 오류는 기록하고 다음 줄로
            out["error"] = f"{e.__class__.__name__}: {e}"
        yield out


def _rule_grade(text, key_facts, chain, counter, card_id=None):
    from generate import rule_judge
    return rule_judge.grade(text, key_facts, chain, counter)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="판단 근거 일괄 채점 → CSV")
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--rule-only", action="store_true", help="Claude 를 부르지 않고 규칙 채점만 한다")
    args = p.parse_args(argv)

    if args.rule_only:
        grade_fn = _rule_grade
    else:
        from generate.judge import grade as grade_fn

    with args.input.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and "answer" not in rows[0]:
        print("입력 CSV 에 answer 열이 없어요.", file=sys.stderr)
        return 2

    n_fail = n_rule = 0
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for i, out in enumerate(grade_rows(rows, grade_fn), 1):
            w.writerow(out)
            n_fail += "score" not in out
            n_rule += out.get("grader") == "rule"
            print(f"[{i}/{len(rows)}] id={out['id']} score={out.get('score', '-')} grader={out.get('grader', '-')}"
                  + (f" error={out['error']}" if out.get("error") else ""))
    print(f"완료: {len(rows)}개 → {args.output} (채점 못함 {n_fail}, 규칙 채점 {n_rule})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
