"""작은 Datalog 엔진 (B, #156). 사실(fact)과 규칙(rule)만 받아, 새 결론이 안 나올 때까지 규칙을 적용한다(고정점).

교수님 피드백("결국 if문 반복 아니냐")과 멘토님 제안(4-3)에 따라, 개념 사전의 판단 기준을 탐색 코드가 아니라
읽을 수 있는 규칙(concepts/rules.dl)으로 분리하려고 만들었다. 정적 프로그램 분석에서 Datalog 로 분석 규칙을 쓰고
고정점까지 계산하는 것과 같은 방식이다.

규칙 문법 (쓰는 만큼만)
    effect(X, Y, S) :- edge(X, Y, S).                         규칙: 오른쪽이 모두 참이면 왼쪽도 참
    effect(X, Z, S1 * S2) :- effect(X, Y, S1), edge(Y, Z, S2).  머리(왼쪽)에서는 곱(*)을 쓸 수 있다
    edge("a", "b", 1).                                         사실: 그냥 참
- 대문자나 _ 로 시작하면 변수, 정수·"따옴표 문자열"·소문자 이름은 상수. _ 하나는 이름 없는 변수(매번 다른 변수)
- % 나 // 뒤는 주석
- 머리의 변수는 몸통에 나와야 한다(안전 규칙). 곱은 머리에서만, 정수끼리만 쓸 수 있다
- 부정(!)은 아직 없다 (조건부 연결·국면은 다음 단계)

계산 방식: semi-naive evaluation
    매 회차에 "지난 회차에 새로 나온 사실(Δ)"이 몸통 어딘가에 하나 이상 들어간 조합만 다시 본다.
    이미 써 본 사실끼리의 조합은 다시 계산하지 않는다. 새 사실이 하나도 안 나오면 멈춘다(고정점).
    값의 종류가 유한하면(개념 사전은 부호가 ±1 뿐) 순환이 있어도 반드시 멈춘다.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

MAX_ROUNDS = 10_000  # 곱이 끝없이 커지는 잘못된 규칙을 막는 안전장치 (개념 사전은 몇 회차면 끝난다)

Fact = tuple  # 상수만 담긴 튜플. 예: ("rate_cut", "bond_yield", -1)


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Product:
    """머리에서만 쓰는 정수 곱. 예: S1 * S2."""
    factors: tuple


@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple[Atom, ...]

    def __str__(self) -> str:
        return f"{_fmt(self.head)} :- {', '.join(_fmt(a) for a in self.body)}."


@dataclass
class Program:
    rules: list[Rule] = field(default_factory=list)
    facts: dict[str, set[Fact]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class Result:
    relations: dict[str, set[Fact]]
    rounds: int  # 고정점에 닿기까지 돈 회차 (마지막 "새 사실 없음" 회차 포함)

    def get(self, pred: str) -> set[Fact]:
        return self.relations.get(pred, set())


class DatalogError(ValueError):
    pass


# ------------------------------------------------------------------
# 읽기 (규칙 파일 → Program)
# ------------------------------------------------------------------

_TOKEN = re.compile(r'\s*(?:(:-)|([(),.*])|(-?\d+)|("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_]*))')


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        in_str = False
        for i, ch in enumerate(line):
            if ch == '"':
                in_str = not in_str
            elif not in_str and (ch == "%" or line.startswith("//", i)):
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _tokens(text: str) -> list[tuple[str, str]]:
    text = _strip_comments(text)
    pos, out = 0, []
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            near = text[pos:pos + 20].strip()
            raise DatalogError(f"읽을 수 없는 글자예요: {near!r}")
        kind = ("arrow", "punct", "int", "str", "name")[m.lastindex - 1]
        out.append((kind, m.group(m.lastindex)))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str):
        self.toks = _tokens(text)
        self.i = 0
        self.anon = 0

    def peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, value: str | None = None, kind: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok is None or (value is not None and tok[1] != value) or (kind is not None and tok[0] != kind):
            want = value or kind
            raise DatalogError(f"{want!r} 가 와야 하는데 {tok[1] if tok else '끝'!r} 가 왔어요")
        self.i += 1
        return tok

    def program(self) -> Program:
        prog = Program()
        while self.peek() is not None:
            head = self.atom()
            if self.peek() == ("arrow", ":-"):
                self.take(":-")
                body = [self.atom()]
                while self.peek() == ("punct", ","):
                    self.take(",")
                    body.append(self.atom())
                self.take(".")
                prog.rules.append(_check_rule(Rule(head, tuple(body))))
            else:
                self.take(".")
                if any(not _is_const(a) for a in head.args):
                    raise DatalogError(f"사실에는 변수나 곱을 쓸 수 없어요: {_fmt(head)}")
                prog.facts[head.pred].add(head.args)
        return prog

    def atom(self) -> Atom:
        pred = self.take(kind="name")[1]
        if pred[0].isupper() or pred[0] == "_":
            raise DatalogError(f"관계 이름은 소문자로 시작해야 해요: {pred}")
        self.take("(")
        args = [self.term()]
        while self.peek() == ("punct", ","):
            self.take(",")
            args.append(self.term())
        self.take(")")
        return Atom(pred, tuple(args))

    def term(self):
        factors = [self.factor()]
        while self.peek() == ("punct", "*"):
            self.take("*")
            factors.append(self.factor())
        return factors[0] if len(factors) == 1 else Product(tuple(factors))

    def factor(self):
        kind, value = self.take()
        if kind == "int":
            return int(value)
        if kind == "str":
            return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if kind == "name":
            if value == "_":
                self.anon += 1
                return Var(f"_{self.anon}")
            return Var(value) if value[0].isupper() or value[0] == "_" else value
        raise DatalogError(f"값이 와야 하는데 {value!r} 가 왔어요")


def _is_const(t) -> bool:
    return isinstance(t, (int, str))


def _vars(atom: Atom) -> set[str]:
    out = set()
    for a in atom.args:
        if isinstance(a, Var):
            out.add(a.name)
        elif isinstance(a, Product):
            out |= {f.name for f in a.factors if isinstance(f, Var)}
    return out


def _check_rule(rule: Rule) -> Rule:
    body_vars = set().union(*(_vars(a) for a in rule.body))
    for a in rule.body:
        if any(isinstance(t, Product) for t in a.args):
            raise DatalogError(f"곱(*)은 머리에서만 쓸 수 있어요: {rule}")
    unsafe = sorted(v for v in _vars(rule.head) if v not in body_vars)
    if unsafe:
        raise DatalogError(f"머리의 변수 {', '.join(unsafe)} 가 몸통에 없어요: {rule}")
    if any(v.startswith("_") for v in _vars(rule.head)):
        raise DatalogError(f"머리에는 이름 없는 변수(_)를 쓸 수 없어요: {rule}")
    return rule


def parse(text: str) -> Program:
    """규칙 파일 글 → Program (규칙 목록, 파일 안의 사실)."""
    return _Parser(text).program()


# ------------------------------------------------------------------
# 계산 (semi-naive 고정점)
# ------------------------------------------------------------------

def _match(atom: Atom, fact: Fact, binding: dict) -> dict | None:
    if len(fact) != len(atom.args):
        return None
    out = binding
    for t, v in zip(atom.args, fact):
        if isinstance(t, Var):
            if t.name in out:
                if out[t.name] != v:
                    return None
            else:
                out = {**out, t.name: v}
        elif t != v:
            return None
    return out


def _join(body: tuple[Atom, ...], delta_at: int, delta: dict, total: dict, i: int = 0, binding: dict | None = None):
    """몸통을 왼쪽부터 맞춰 나가며 가능한 변수 묶음을 낸다. delta_at 번째 원자만 Δ 에서, 나머지는 전체에서 찾는다."""
    binding = binding if binding is not None else {}
    if i == len(body):
        yield binding
        return
    atom = body[i]
    source = delta if i == delta_at else total
    for fact in source.get(atom.pred, ()):
        b = _match(atom, fact, binding)
        if b is not None:
            yield from _join(body, delta_at, delta, total, i + 1, b)


def _ground(head: Atom, binding: dict) -> Fact:
    out = []
    for t in head.args:
        if isinstance(t, Var):
            out.append(binding[t.name])
        elif isinstance(t, Product):
            value = 1
            for f in t.factors:
                v = binding[f.name] if isinstance(f, Var) else f
                if not isinstance(v, int) or isinstance(v, bool):
                    raise DatalogError(f"곱은 정수끼리만 할 수 있어요: {v!r}")
                value *= v
            out.append(value)
        else:
            out.append(t)
    return tuple(out)


def evaluate(program: Program, facts: dict[str, set[Fact]] | None = None) -> Result:
    """규칙을 사실에 적용해 새 사실이 안 나올 때까지 반복한다. facts 는 파일 밖에서 넣는 사실(개념 사전 연결 등)."""
    total: dict[str, set[Fact]] = defaultdict(set)
    for source in (program.facts, facts or {}):
        for pred, rows in source.items():
            total[pred] |= {tuple(r) for r in rows}
    delta = {p: set(rows) for p, rows in total.items()}  # 1회차: 처음 사실이 모두 "새 사실"

    rounds = 0
    while any(delta.values()):
        rounds += 1
        if rounds > MAX_ROUNDS:
            raise DatalogError(f"{MAX_ROUNDS}회차가 넘도록 끝나지 않아요 (곱이 계속 커지는 규칙인지 확인)")
        new: dict[str, set[Fact]] = defaultdict(set)
        for rule in program.rules:
            for k, atom in enumerate(rule.body):
                if not delta.get(atom.pred):
                    continue
                for binding in _join(rule.body, k, delta, total):
                    fact = _ground(rule.head, binding)
                    if fact not in total[rule.head.pred]:
                        new[rule.head.pred].add(fact)
        for pred, rows in new.items():
            total[pred] |= rows
        delta = new
    return Result(relations=dict(total), rounds=rounds)


def _fmt(atom: Atom) -> str:
    def term(t):
        if isinstance(t, Var):
            return "_" if t.name.startswith("_") else t.name
        if isinstance(t, Product):
            return " * ".join(term(f) for f in t.factors)
        return f'"{t}"' if isinstance(t, str) else str(t)
    return f"{atom.pred}({', '.join(term(a) for a in atom.args)})"
