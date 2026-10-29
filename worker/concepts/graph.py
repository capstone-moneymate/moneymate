"""개념 사전 경로 탐색 (B). 개념 사이의 연결(올리는 힘 / 누르는 힘)을 부호 있는 방향 그래프로 읽고,
시작 개념에서 결과 개념까지의 경로·최종 방향·모호성을 코드가 계산한다.

실행 (worker/ 에서):
    python -m concepts.graph                                        # 순환 검사 + 모호한 개념 쌍 목록
    python -m concepts.graph --from rate_cut --to growth_valuation  # 두 개념 사이 경로와 방향
    python -m concepts.graph --from rate_cut --to growth_valuation --change down   # 시작 개념이 줄어드는 사건

규칙 (docs/modules/concept_dictionary.md)
- 연결은 "from 이 커지면 to 를 올린다(up = +1) / 누른다(down = -1)"로 읽는다
- 경로의 부호 = 연결 부호의 곱. 시작 개념이 줄어드는 사건이면 한 번 더 뒤집는다
- 같은 두 개념 사이에 부호가 다른 경로가 함께 있으면 모호(ambiguous). 순서 맞추기 정답으로 쓰지 않는다
- 경로는 같은 개념을 두 번 지나지 않는 경로만 센다. 개념 사전에는 순환이 없어야 한다
"""
import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

SEEDS = Path(__file__).resolve().parents[2] / "db" / "seeds"
UP, DOWN, AMBIGUOUS = "up", "down", "ambiguous"
SIGN = {UP: 1, DOWN: -1}


@dataclass
class Graph:
    names: dict[str, str]                                 # concept id -> 이름
    out: dict[str, list[tuple[str, int]]] = field(default_factory=dict)   # from -> [(to, ±1)]


@dataclass
class Effect:
    start: str
    end: str
    paths: list[tuple[list[str], int]]   # (경로, 그 경로로 본 결과의 부호)
    direction: str | None                # up / down / ambiguous / None(경로 없음)


def load_graph(seeds_dir: Path = SEEDS) -> Graph:
    """seeds CSV(concepts.csv, causal_edges.csv) -> Graph. 사전에 없는 개념을 잇는 연결이나 force_dir 오타는 에러."""
    with open(seeds_dir / "concepts.csv", encoding="utf-8", newline="") as f:
        names = {r["id"]: r["name"] for r in csv.DictReader(f)}
    with open(seeds_dir / "causal_edges.csv", encoding="utf-8", newline="") as f:
        edges = [(r["from_concept"], r["to_concept"], r["force_dir"]) for r in csv.DictReader(f)]
    return build_graph(names, edges)


def build_graph(names: dict[str, str], edges: list[tuple[str, str, str]]) -> Graph:
    g = Graph(names=dict(names), out={cid: [] for cid in names})
    for src, dst, force in edges:
        for cid in (src, dst):
            if cid not in names:
                raise ValueError(f"개념 사전에 없는 개념: {cid} ({src} -> {dst})")
        if force not in SIGN:
            raise ValueError(f"force_dir 는 up / down 중 하나: {force} ({src} -> {dst})")
        g.out[src].append((dst, SIGN[force]))
    return g


def find_cycle(g: Graph) -> list[str] | None:
    """순환이 있으면 그 순환(시작 개념이 끝에 한 번 더 나옴), 없으면 None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in g.out}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GRAY
        stack.append(node)
        for nxt, _ in g.out[node]:
            if color[nxt] == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == WHITE and (cyc := visit(nxt)):
                return cyc
        stack.pop()
        color[node] = BLACK
        return None

    for cid in sorted(g.out):
        if color[cid] == WHITE and (cyc := visit(cid)):
            return cyc
    return None


def signed_paths(g: Graph, start: str, end: str) -> list[tuple[list[str], int]]:
    """start -> end 의 모든 단순 경로와 그 경로의 부호(연결 부호의 곱). 짧은 경로부터, 같으면 이름순."""
    for cid in (start, end):
        if cid not in g.out:
            raise ValueError(f"개념 사전에 없는 개념: {cid}")
    found = []

    def walk(node: str, path: list[str], sign: int) -> None:
        if node == end and len(path) > 1:
            found.append((list(path), sign))
            return
        for nxt, s in g.out[node]:
            if nxt not in path:
                path.append(nxt)
                walk(nxt, path, sign * s)
                path.pop()

    walk(start, [start], 1)
    return sorted(found, key=lambda p: (len(p[0]), p[0]))


def effect(g: Graph, start: str, end: str, change: str = UP) -> Effect:
    """start 가 change(up: 커짐/일어남, down: 줄어듦) 했을 때 end 가 받는 힘.
    모든 경로의 부호가 같으면 그 방향, 다르면 ambiguous, 경로가 없으면 None."""
    paths = [(p, s * SIGN[change]) for p, s in signed_paths(g, start, end)]
    signs = {s for _, s in paths}
    if not signs:
        direction = None
    elif len(signs) > 1:
        direction = AMBIGUOUS
    else:
        direction = UP if signs.pop() == 1 else DOWN
    return Effect(start=start, end=end, paths=paths, direction=direction)


def ambiguous_pairs(g: Graph) -> list[Effect]:
    """방향이 다른 경로가 함께 있는 (시작, 결과) 쌍 전부."""
    out = []
    for start in sorted(g.out):
        for end in sorted(g.out):
            if start != end:
                e = effect(g, start, end)
                if e.direction == AMBIGUOUS:
                    out.append(e)
    return out


def format_path(g: Graph, path: list[str]) -> str:
    return " → ".join(g.names[c] for c in path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="개념 사전 경로·방향·모호성")
    parser.add_argument("--from", dest="start", help="시작 개념 id (예: rate_cut)")
    parser.add_argument("--to", dest="end", help="결과 개념 id (예: growth_valuation)")
    parser.add_argument("--change", choices=[UP, DOWN], default=UP, help="시작 개념이 커지면 up, 줄어들면 down")
    args = parser.parse_args(argv)
    g = load_graph()
    label = {UP: "상승 압력 ▲", DOWN: "하락 압력 ▼", AMBIGUOUS: "모호 (방향이 다른 경로가 함께 있음)", None: "경로 없음"}

    if args.start or args.end:
        if not (args.start and args.end):
            print("--from 과 --to 를 함께 주세요.")
            return 1
        e = effect(g, args.start, args.end, args.change)
        print(f"{g.names[e.start]}({'커짐' if args.change == UP else '줄어듦'}) → {g.names[e.end]}: {label[e.direction]}")
        for path, s in e.paths:
            print(f"  {'▲' if s == 1 else '▼'} {format_path(g, path)}")
        return 0

    n_edges = sum(len(v) for v in g.out.values())
    print(f"개념 {len(g.names)}개, 연결 {n_edges}개")
    cyc = find_cycle(g)
    print("순환: 없음" if cyc is None else f"순환: 있음 ({format_path(g, cyc)})")
    pairs = ambiguous_pairs(g)
    print(f"모호한 개념 쌍: {len(pairs)}개")
    for e in pairs:
        print(f"- {g.names[e.start]} → {g.names[e.end]}")
        for path, s in e.paths:
            print(f"    {'▲' if s == 1 else '▼'} {format_path(g, path)}")
    return 1 if cyc else 0


if __name__ == "__main__":
    sys.exit(main())
