"""개념 사전 적재 (B). db/seeds 의 concepts.csv, causal_edges.csv 를 concepts, causal_edges 테이블에 넣는다.

실행 (worker/ 에서):
    python -m concepts.loader          # 적재해 보고 결과만 출력 (되돌림)
    python -m concepts.loader --save   # DB 에 반영

규칙 (docs/modules/concept_dictionary.md)
- CSV 가 원본이다. 여러 번 돌려도 결과가 같고, 고친 이름·별칭·방향·note 는 덮어쓴다
- CSV 에서 지운 연결은 DB 에서도 지운다. 개념은 cards, user_concepts 가 참조할 수 있어 지우지 않고 경고만 한다
- 넣기 전에 사전이 올바른지 검사한다: 중복, 사전에 없는 개념, force_dir 오타, 순환
"""
import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from concepts.graph import SEEDS, build_graph, find_cycle


@dataclass
class Seeds:
    concepts: list[tuple[str, str, str, str, list[str]]]  # (id, name, theme, kind, aliases)
    edges: list[tuple[str, str, str, str]]                # (from, to, force_dir, note)


def parse_aliases(text: str) -> list[str]:
    """"금리 인상;금리 올림" -> ["금리 인상", "금리 올림"]. 비어 있으면 빈 목록."""
    return [a.strip() for a in (text or "").split(";") if a.strip()]


def read_seeds(seeds_dir: Path = SEEDS) -> Seeds:
    """CSV 를 읽고 검사한다. 사전이 잘못됐으면 DB 에 넣기 전에 ValueError."""
    with open(seeds_dir / "concepts.csv", encoding="utf-8", newline="") as f:
        concepts = [(r["id"], r["name"], r["theme"], r["kind"], parse_aliases(r["aliases"]))
                    for r in csv.DictReader(f)]
    with open(seeds_dir / "causal_edges.csv", encoding="utf-8", newline="") as f:
        edges = [(r["from_concept"], r["to_concept"], r["force_dir"], r["note"]) for r in csv.DictReader(f)]

    repeated_ids = [c for c, n in Counter(c[0] for c in concepts).items() if n > 1]
    if repeated_ids:
        raise ValueError(f"개념 id 가 중복됨: {', '.join(repeated_ids)}")
    repeated_edges = [e for e, n in Counter(e[:2] for e in edges).items() if n > 1]
    if repeated_edges:
        raise ValueError("연결이 중복됨: " + ", ".join(f"{a} -> {b}" for a, b in repeated_edges))

    g = build_graph({c[0]: c[1] for c in concepts}, [e[:3] for e in edges])  # 없는 개념·force_dir 오타는 여기서 에러
    cycle = find_cycle(g)
    if cycle:
        raise ValueError("연결에 순환이 있음: " + " -> ".join(cycle))
    return Seeds(concepts, edges)


def apply_seeds(conn, seeds: Seeds) -> dict[str, list]:
    """DB 를 CSV 와 맞춘다. 커밋은 부르는 쪽이 한다. 지운 연결과 CSV 에 없는 개념을 돌려준다."""
    with conn.cursor() as cur:
        for row in seeds.concepts:
            cur.execute(
                """INSERT INTO concepts (id, name, theme, kind, aliases) VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, theme = EXCLUDED.theme,
                       kind = EXCLUDED.kind, aliases = EXCLUDED.aliases""",
                row,
            )
        for row in seeds.edges:
            cur.execute(
                """INSERT INTO causal_edges (from_concept, to_concept, force_dir, note) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (from_concept, to_concept) DO UPDATE SET force_dir = EXCLUDED.force_dir,
                       note = EXCLUDED.note""",
                row,
            )

        wanted = {e[:2] for e in seeds.edges}
        cur.execute("SELECT from_concept, to_concept FROM causal_edges")
        removed = sorted(e for e in map(tuple, cur.fetchall()) if e not in wanted)
        for src, dst in removed:
            cur.execute("DELETE FROM causal_edges WHERE from_concept = %s AND to_concept = %s", (src, dst))

        ids = {c[0] for c in seeds.concepts}
        cur.execute("SELECT id FROM concepts")
        extra = sorted(c for (c,) in cur.fetchall() if c not in ids)
    return {"removed_edges": removed, "extra_concepts": extra}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="개념 사전 CSV 를 DB 에 적재")
    parser.add_argument("--save", action="store_true", help="DB 에 반영 (없으면 적재 후 되돌림)")
    args = parser.parse_args(argv)
    seeds = read_seeds()

    from db import get_conn
    conn = get_conn()
    try:
        result = apply_seeds(conn, seeds)
        print(f"개념 {len(seeds.concepts)}개, 연결 {len(seeds.edges)}개")
        for src, dst in result["removed_edges"]:
            print(f"  지운 연결: {src} -> {dst}")
        for cid in result["extra_concepts"]:
            print(f"  경고: CSV 에 없는 개념이 DB 에 남아 있음: {cid} (참조를 확인한 뒤 직접 지울 것)")
        if args.save:
            conn.commit()
            print("\nDB 에 반영했습니다.")
        else:
            conn.rollback()
            print("\n출력만 했습니다. 반영하려면 --save 를 붙이세요.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
