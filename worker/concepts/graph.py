"""개념 사전 경로 탐색 (B). 개념 사이의 연결(올리는 힘 / 누르는 힘)을 부호 있는 방향 그래프로 읽고,
시작 개념에서 결과 개념까지의 경로·최종 방향·모호성을 계산한다.

방향과 모호성은 규칙(concepts/rules.dl)을 Datalog 엔진(concepts/datalog.py)으로 고정점까지 계산해 정한다 (#156).
경로 나열(퀴즈 정답 순서)은 아래 signed_paths 가 하고, effect() 가 두 결과가 같은지 매번 확인한다.
국면(regime)별 조건부 연결은 db/seeds/cond_edges.csv 의 사실과 rules.dl 4~6 규칙으로 계산한다 (#158).
국면을 주지 않으면 평상시(normal)라 조건부 연결이 없던 때와 결과가 같다.

실행 (worker/ 에서):
    python -m concepts.graph                                        # 순환 검사 + 모호한 개념 쌍 목록
    python -m concepts.graph --from rate_cut --to growth_valuation  # 두 개념 사이 경로와 방향
    python -m concepts.graph --from rate_cut --to growth_valuation --change down   # 시작 개념이 줄어드는 사건
    python -m concepts.graph --from rate_cut --to growth_valuation --regime recession  # 경기 침체 국면

규칙 (docs/modules/concept_dictionary.md)
- 연결은 "from 이 커지면 to 를 올린다(up = +1) / 누른다(down = -1)"로 읽는다
- 경로의 부호 = 연결 부호의 곱. 시작 개념이 줄어드는 사건이면 한 번 더 뒤집는다
- 같은 두 개념 사이에 부호가 다른 경로가 함께 있으면 모호(ambiguous). 순서 맞추기 정답으로 쓰지 않는다
- 경로는 같은 개념을 두 번 지나지 않는 경로만 센다. 개념 사전에는 순환이 없어야 한다 (평상시와 국면마다, find_any_cycle)
"""
import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from concepts import datalog

SEEDS = Path(__file__).resolve().parents[2] / "db" / "seeds"
RULES = Path(__file__).with_name("rules.dl")
UP, DOWN, AMBIGUOUS = "up", "down", "ambiguous"
SIGN = {UP: 1, DOWN: -1}
NORMAL = "normal"                       # 평상시 국면. 조건부 연결이 없는 기본 연결만 쓴다
REGIME_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class Graph:
    names: dict[str, str]                                 # concept id -> 이름
    out: dict[str, list[tuple[str, int]]] = field(default_factory=dict)   # from -> [(to, ±1)]
    cond: list[tuple[str, str, int, str]] = field(default_factory=list)   # 조건부 연결 (from, to, ±1, 국면)


@dataclass
class Effect:
    start: str
    end: str
    paths: list[tuple[list[str], int]]   # (경로, 그 경로로 본 결과의 부호)
    direction: str | None                # up / down / ambiguous / None(경로 없음)
    regime: str = NORMAL


def load_graph(seeds_dir: Path = SEEDS) -> Graph:
    """seeds CSV(concepts.csv, causal_edges.csv, cond_edges.csv) -> Graph.
    사전에 없는 개념을 잇는 연결이나 force_dir·국면 이름 오타는 에러. cond_edges.csv 가 없으면 조건부 연결 없음."""
    with open(seeds_dir / "concepts.csv", encoding="utf-8", newline="") as f:
        names = {r["id"]: r["name"] for r in csv.DictReader(f)}
    with open(seeds_dir / "causal_edges.csv", encoding="utf-8", newline="") as f:
        edges = [(r["from_concept"], r["to_concept"], r["force_dir"]) for r in csv.DictReader(f)]
    cond = []
    if (seeds_dir / "cond_edges.csv").exists():
        with open(seeds_dir / "cond_edges.csv", encoding="utf-8", newline="") as f:
            cond = [(r["from_concept"], r["to_concept"], r["force_dir"], r["regime"]) for r in csv.DictReader(f)]
    return build_graph(names, edges, cond)


def _check_edge(names: dict[str, str], src: str, dst: str, force: str) -> None:
    for cid in (src, dst):
        if cid not in names:
            raise ValueError(f"개념 사전에 없는 개념: {cid} ({src} -> {dst})")
    if force not in SIGN:
        raise ValueError(f"force_dir 는 up / down 중 하나: {force} ({src} -> {dst})")


def build_graph(names: dict[str, str], edges: list[tuple[str, str, str]],
                cond: list[tuple[str, str, str, str]] | None = None) -> Graph:
    """cond: 조건부 연결 (from, to, up/down, 국면). 국면 이름은 영문 소문자+밑줄이고 normal 은 쓸 수 없다."""
    g = Graph(names=dict(names), out={cid: [] for cid in names})
    for src, dst, force in edges:
        _check_edge(names, src, dst, force)
        g.out[src].append((dst, SIGN[force]))
    seen: dict[tuple[str, str, str], int] = {}
    for src, dst, force, regime in cond or []:
        _check_edge(names, src, dst, force)
        if not REGIME_ID.match(regime) or regime == NORMAL:
            raise ValueError(f"국면 이름은 영문 소문자와 밑줄이고 {NORMAL} 은 쓸 수 없어요: {regime!r} ({src} -> {dst})")
        if seen.get((src, dst, regime), SIGN[force]) != SIGN[force]:
            raise ValueError(f"같은 국면에 같은 연결의 방향이 둘이에요: {src} -> {dst} ({regime})")
        seen[(src, dst, regime)] = SIGN[force]
        g.cond.append((src, dst, SIGN[force], regime))
    return g


def regimes(g: Graph) -> list[str]:
    """평상시와 조건부 연결에 나오는 국면들."""
    return [NORMAL] + sorted({r for *_, r in g.cond})


def regime_out(g: Graph, regime: str = NORMAL) -> dict[str, list[tuple[str, int]]]:
    """그 국면에서 쓰는 연결 (경로 나열용). rules.dl 의 edge_r 과 같은 뜻: 조건부 연결이 있으면 기본 연결을 대신한다."""
    if regime == NORMAL:
        return g.out
    if regime not in regimes(g):
        raise ValueError(f"모르는 국면: {regime} (있는 국면: {', '.join(regimes(g))})")
    over = {(s, d): sign for s, d, sign, r in g.cond if r == regime}
    out = {src: [(dst, s) for dst, s in outs if (src, dst) not in over] for src, outs in g.out.items()}
    for (src, dst), sign in over.items():
        out[src].append((dst, sign))
    return out


def find_cycle(g: Graph, regime: str = NORMAL) -> list[str] | None:
    """그 국면의 연결에 순환이 있으면 그 순환(시작 개념이 끝에 한 번 더 나옴), 없으면 None."""
    out = regime_out(g, regime)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in out}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = GRAY
        stack.append(node)
        for nxt, _ in out[node]:
            if color[nxt] == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == WHITE and (cyc := visit(nxt)):
                return cyc
        stack.pop()
        color[node] = BLACK
        return None

    for cid in sorted(out):
        if color[cid] == WHITE and (cyc := visit(cid)):
            return cyc
    return None


def find_any_cycle(g: Graph) -> tuple[str, list[str]] | None:
    """평상시와 모든 국면을 본다. 조건부 연결만으로 생기는 순환(예: 침체 때만 b → a)도 잡는다. (국면, 순환) 또는 None."""
    for r in regimes(g):
        if cyc := find_cycle(g, r):
            return r, cyc
    return None


def signed_paths(g: Graph, start: str, end: str, regime: str = NORMAL) -> list[tuple[list[str], int]]:
    """start -> end 의 모든 단순 경로와 그 경로의 부호(연결 부호의 곱). 짧은 경로부터, 같으면 이름순.
    regime 을 주면 그 국면의 연결(조건부 연결이 기본 연결을 대신함)로 찾는다."""
    for cid in (start, end):
        if cid not in g.out:
            raise ValueError(f"개념 사전에 없는 개념: {cid}")
    out = regime_out(g, regime)
    found = []

    def walk(node: str, path: list[str], sign: int) -> None:
        if node == end and len(path) > 1:
            found.append((list(path), sign))
            return
        for nxt, s in out[node]:
            if nxt not in path:
                path.append(nxt)
                walk(nxt, path, sign * s)
                path.pop()

    walk(start, [start], 1)
    return sorted(found, key=lambda p: (len(p[0]), p[0]))


@dataclass(frozen=True)
class Derived:
    """규칙 엔진이 낸 결론. effects[(시작, 결과)] = 평상시 받는 영향의 부호들, ambiguous = 평상시 모호한 쌍.
    effects_r[(시작, 결과, 국면)]·ambiguous_r 은 국면별 결론(rules.dl 4~6)."""
    effects: dict[tuple[str, str], frozenset[int]]
    ambiguous: frozenset[tuple[str, str]]
    rounds: int
    effects_r: dict[tuple[str, str, str], frozenset[int]] = field(default_factory=dict)
    ambiguous_r: frozenset[tuple[str, str, str]] = frozenset()
    strata: int = 1


@lru_cache(maxsize=1)
def _rules() -> datalog.Program:
    return datalog.parse(RULES.read_text(encoding="utf-8"))


def edge_facts(g: Graph) -> frozenset[tuple[str, str, int]]:
    """연결 → Datalog 사실 edge(원인, 결과, 부호)."""
    return frozenset((src, dst, s) for src, outs in g.out.items() for dst, s in outs)


def _group(rows) -> dict:
    out: dict = {}
    for *key, s in rows:
        out.setdefault(tuple(key), set()).add(s)
    return {k: frozenset(v) for k, v in out.items()}


@lru_cache(maxsize=32)
def _derive(edges: frozenset[tuple[str, str, int]], cond: frozenset[tuple[str, str, int, str]]) -> Derived:
    facts = {"edge": set(edges), "cond_edge": set(cond),
             "regime": {(NORMAL,)} | {(r,) for *_, r in cond}}
    result = datalog.evaluate(_rules(), facts)
    # effect_r 은 (X, Y, S, R) 라 부호를 맨 뒤로 옮겨 묶는다
    effects_r = _group((x, y, r, s) for x, y, s, r in result.get("effect_r"))
    return Derived(effects=_group(result.get("effect")), ambiguous=frozenset(result.get("ambiguous")),
                   rounds=result.rounds, effects_r=effects_r, ambiguous_r=frozenset(result.get("ambiguous_r")),
                   strata=result.strata)


def derive(g: Graph) -> Derived:
    """그래프의 연결에 규칙을 고정점까지 적용한 결론. 연결이 같으면 다시 계산하지 않는다."""
    return _derive(edge_facts(g), frozenset(g.cond))


def effect(g: Graph, start: str, end: str, change: str = UP, regime: str = NORMAL) -> Effect:
    """start 가 change(up: 커짐/일어남, down: 줄어듦) 했을 때 end 가 받는 힘.
    받는 영향이 한 방향이면 그 방향, 두 방향 모두면 ambiguous, 없으면 None.

    방향은 규칙 엔진(rules.dl)의 결론이고, paths 는 그 결론을 이루는 경로(퀴즈 정답 순서용)다.
    두 계산이 어긋나면(사전에 순환이 생긴 경우 등) 조용히 넘어가지 않고 오류를 낸다.
    regime 을 주면 그 국면의 결론(조건부 연결 반영)이다. 주지 않으면 평상시라 예전과 같다.
    """
    paths = [(p, s * SIGN[change]) for p, s in signed_paths(g, start, end, regime)]
    d = derive(g)
    if regime == NORMAL:
        raw, amb = d.effects.get((start, end), frozenset()), (start, end) in d.ambiguous
    else:
        raw, amb = d.effects_r.get((start, end, regime), frozenset()), (start, end, regime) in d.ambiguous_r
    signs = {s * SIGN[change] for s in raw}
    if signs != {s for _, s in paths} or amb != (len(signs) > 1):
        raise RuntimeError(f"규칙 엔진과 경로 계산이 달라요: {start} → {end} ({regime}) "
                           f"(엔진 {sorted(signs)}, 경로 {sorted({s for _, s in paths})}). 사전에 순환이 있는지 확인하세요")
    if not signs:
        direction = None
    elif len(signs) > 1:
        direction = AMBIGUOUS
    else:
        direction = UP if signs.pop() == 1 else DOWN
    return Effect(start=start, end=end, paths=paths, direction=direction, regime=regime)


def ambiguous_pairs(g: Graph, regime: str = NORMAL) -> list[Effect]:
    """방향이 다른 경로가 함께 있는 (시작, 결과) 쌍 전부. 규칙 ambiguous(X, Y) / ambiguous_r(X, Y, R) 의 결론이다."""
    d = derive(g)
    if regime == NORMAL:
        pairs = sorted(d.ambiguous)
    else:
        regime_out(g, regime)  # 모르는 국면이면 오류
        pairs = sorted((x, y) for x, y, r in d.ambiguous_r if r == regime)
    return [effect(g, start, end, regime=regime) for start, end in pairs]


def format_path(g: Graph, path: list[str]) -> str:
    return " → ".join(g.names[c] for c in path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="개념 사전 경로·방향·모호성")
    parser.add_argument("--from", dest="start", help="시작 개념 id (예: rate_cut)")
    parser.add_argument("--to", dest="end", help="결과 개념 id (예: growth_valuation)")
    parser.add_argument("--change", choices=[UP, DOWN], default=UP, help="시작 개념이 커지면 up, 줄어들면 down")
    parser.add_argument("--regime", default=NORMAL, help="국면 (기본 normal = 평상시, 예: recession)")
    args = parser.parse_args(argv)
    g = load_graph()
    label = {UP: "상승 압력 ▲", DOWN: "하락 압력 ▼", AMBIGUOUS: "모호 (방향이 다른 경로가 함께 있음)", None: "경로 없음"}

    if args.start or args.end:
        if not (args.start and args.end):
            print("--from 과 --to 를 함께 주세요.")
            return 1
        try:
            e = effect(g, args.start, args.end, args.change, args.regime)
        except ValueError as err:
            parser.error(str(err))
        print(f"[{e.regime}] {g.names[e.start]}({'커짐' if args.change == UP else '줄어듦'}) → {g.names[e.end]}: "
              f"{label[e.direction]}")
        for path, s in e.paths:
            print(f"  {'▲' if s == 1 else '▼'} {format_path(g, path)}")
        return 0

    n_edges = sum(len(v) for v in g.out.values())
    print(f"개념 {len(g.names)}개, 연결 {n_edges}개, 조건부 연결 {len(g.cond)}개 (국면: {', '.join(regimes(g))})")
    found = find_any_cycle(g)
    print("순환: 없음" if found is None else f"순환: 있음 [{found[0]}] ({format_path(g, found[1])})")
    if found:
        return 1
    d = derive(g)
    print(f"규칙 엔진(rules.dl): {d.strata}개 층, {d.rounds}회차에 고정점, "
          f"평상시 영향 결론 {sum(len(v) for v in d.effects.values())}개")
    for r in regimes(g):
        pairs = ambiguous_pairs(g, r)
        print(f"[{r}] 모호한 개념 쌍: {len(pairs)}개")
        for e in pairs:
            print(f"- {g.names[e.start]} → {g.names[e.end]}")
            for path, s in e.paths:
                print(f"    {'▲' if s == 1 else '▼'} {format_path(g, path)}")
    for src, dst, s, r in g.cond:
        print(f"[{r}] 조건부 연결: {g.names[src]} → {g.names[dst]} {'▲' if s == 1 else '▼'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
