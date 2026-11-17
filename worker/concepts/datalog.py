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
- 머리의 변수는 몸통의 긍정 원자에 나와야 한다(안전 규칙). 곱은 머리에서만, 정수끼리만 쓸 수 있다
- 몸통 원자 앞에 ! 를 붙이면 부정: "그런 사실이 없으면 참" (#158). 예:
    edge_r(X, Y, S, R) :- edge(X, Y, S), regime(R), !overridden(X, Y, R).
  부정 원자의 이름 있는 변수는 긍정 원자에서 먼저 정해져야 한다. _ 는 "아무거나"라서 !p(X, _) 는 "X 로 시작하는 p 가 하나도 없음"

계산 방식: 층별(stratified) semi-naive evaluation
    "B 가 없으면 A" 를 판단하려면 B 를 먼저 다 알아야 한다. 그래서 규칙을 층으로 나눠 B 를 A 보다 아래 층에 두고,
    아래 층부터 차례로 고정점까지 계산한다. "A 가 없으면 A" 처럼 부정이 순환에 걸리면 층을 나눌 수 없어 읽을 때 오류.
    한 층 안에서는 semi-naive: 매 회차에 "지난 회차에 새로 나온 사실(Δ)"이 몸통 어딘가에 하나 이상 들어간 조합만
    다시 본다. 새 사실이 하나도 안 나오면 그 층을 멈춘다(고정점).
    값의 종류가 유한하면(개념 사전은 부호가 ±1 뿐) 순환이 있어도 반드시 멈춘다.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field

MAX_ROUNDS = 10_000  # 곱이 끝없이 커지는 잘못된 규칙을 막는 안전장치 (개념 사전은 몇 회차면 끝난다)
ANON = "_#"          # 이름 없는 변수(_)의 내부 이름 앞머리. # 은 규칙 글에 쓸 수 없어 _1·_X 같은 이름과 겹치지 않는다

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
    negated: bool = False  # 몸통에서 ! 가 붙은 원자


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple[Atom, ...]

    @property
    def positive(self) -> tuple[Atom, ...]:
        return tuple(a for a in self.body if not a.negated)

    @property
    def negative(self) -> tuple[Atom, ...]:
        return tuple(a for a in self.body if a.negated)

    def __str__(self) -> str:
        return f"{_fmt(self.head)} :- {', '.join(_fmt(a) for a in self.body)}."


@dataclass
class Program:
    rules: list[Rule] = field(default_factory=list)
    facts: dict[str, set[Fact]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class Result:
    relations: dict[str, set[Fact]]
    rounds: int      # 고정점에 닿기까지 돈 회차 (층마다 마지막 "새 사실 없음" 회차 포함, 모든 층 합)
    strata: int = 1  # 규칙을 나눈 층 수

    def get(self, pred: str) -> set[Fact]:
        return self.relations.get(pred, set())


class DatalogError(ValueError):
    pass


# ------------------------------------------------------------------
# 읽기 (규칙 파일 → Program)
# ------------------------------------------------------------------

_TOKEN = re.compile(r'\s*(?:(:-)|([(),.*!])|(-?\d+)|("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_]*))')


def _strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        in_str = escaped = False
        for i, ch in enumerate(line):
            if in_str:
                if escaped:
                    escaped = False          # \" 의 따옴표는 문자열을 닫지 않는다
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "%" or line.startswith("//", i):
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
                body = [self.literal()]
                while self.peek() == ("punct", ","):
                    self.take(",")
                    body.append(self.literal())
                self.take(".")
                prog.rules.append(_check_rule(Rule(head, tuple(body))))
            else:
                self.take(".")
                if any(not _is_const(a) for a in head.args):
                    raise DatalogError(f"사실에는 변수나 곱을 쓸 수 없어요: {_fmt(head)}")
                prog.facts[head.pred].add(head.args)
        return prog

    def literal(self) -> Atom:
        """몸통 원자 하나. 앞에 ! 가 있으면 부정."""
        if self.peek() == ("punct", "!"):
            self.take("!")
            a = self.atom()
            return Atom(a.pred, a.args, negated=True)
        return self.atom()

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
                return Var(f"{ANON}{self.anon}")
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
    if not rule.positive:
        raise DatalogError(f"몸통에 ! 없는 원자가 하나 이상 있어야 해요: {rule}")
    body_vars = set().union(*(_vars(a) for a in rule.positive))
    for a in rule.body:
        if any(isinstance(t, Product) for t in a.args):
            raise DatalogError(f"곱(*)은 머리에서만 쓸 수 있어요: {rule}")
    unsafe = sorted(v for v in _vars(rule.head) if v not in body_vars)
    if unsafe:
        raise DatalogError(f"머리의 변수 {', '.join(unsafe)} 가 몸통에 없어요: {rule}")
    if any(v.startswith(ANON) for v in _vars(rule.head)):
        raise DatalogError(f"머리에는 이름 없는 변수(_)를 쓸 수 없어요: {rule}")
    for a in rule.negative:
        free = sorted(v for v in _vars(a) if v not in body_vars and not v.startswith(ANON))
        if free:
            raise DatalogError(f"! 원자의 변수 {', '.join(free)} 가 앞의 긍정 원자에 없어요: {rule}")
    return rule


def stratify(rules: list[Rule]) -> list[list[Rule]]:
    """규칙을 층으로 나눈다. 머리 관계는 몸통 관계보다 같거나 높은 층, ! 로 쓴 관계보다는 높은 층.

    관계가 n 개면 층은 n 을 넘을 수 없어서, 넘으면 부정이 순환에 걸린 것이다("A 가 없으면 A").
    """
    preds = {r.head.pred for r in rules} | {a.pred for r in rules for a in r.body}
    level = dict.fromkeys(preds, 0)
    changed = True
    while changed:
        changed = False
        for r in rules:
            for a in r.body:
                need = level[a.pred] + (1 if a.negated else 0)
                if level[r.head.pred] < need:
                    level[r.head.pred] = need
                    changed = True
                    if need > len(preds):
                        raise DatalogError(f"부정(!)이 순환에 걸려 층을 나눌 수 없어요: {r}")
    out: dict[int, list[Rule]] = defaultdict(list)
    for r in rules:
        out[level[r.head.pred]].append(r)
    return [out[k] for k in sorted(out)]


def parse(text: str) -> Program:
    """규칙 파일 글 → Program (규칙 목록, 파일 안의 사실). 부정이 순환에 걸리면 여기서 오류."""
    prog = _Parser(text).program()
    stratify(prog.rules)
    return prog


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


def _holds_none(atoms: tuple[Atom, ...], binding: dict, total: dict) -> bool:
    """! 원자마다 맞는 사실이 하나도 없으면 True. _ 는 아무 값과 맞는다(아래 층이라 이미 다 계산돼 있다)."""
    return not any(_match(a, f, binding) is not None for a in atoms for f in total.get(a.pred, ()))


def _join(body: tuple[Atom, ...], delta_at: int, delta: dict, total: dict, i: int = 0, binding: dict | None = None,
          negative: tuple[Atom, ...] = ()):
    """긍정 원자를 왼쪽부터 맞춰 나가며 가능한 변수 묶음을 낸다. delta_at 번째 원자만 Δ 에서, 나머지는 전체에서 찾는다.
    끝까지 맞춘 묶음은 ! 원자가 모두 거짓일 때만 낸다."""
    binding = binding if binding is not None else {}
    if i == len(body):
        if not negative or _holds_none(negative, binding, total):
            yield binding
        return
    atom = body[i]
    source = delta if i == delta_at else total
    for fact in source.get(atom.pred, ()):
        b = _match(atom, fact, binding)
        if b is not None:
            yield from _join(body, delta_at, delta, total, i + 1, b, negative)


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
    """규칙을 사실에 적용해 새 사실이 안 나올 때까지 반복한다. facts 는 파일 밖에서 넣는 사실(개념 사전 연결 등).
    층이 여럿이면 아래 층부터 차례로 고정점까지 계산한다."""
    total: dict[str, set[Fact]] = defaultdict(set)
    for source in (program.facts, facts or {}):
        for pred, rows in source.items():
            total[pred] |= {tuple(r) for r in rows}

    strata = stratify(program.rules)
    rounds = 0
    for rules in strata:
        delta = {p: set(rows) for p, rows in total.items()}  # 층의 1회차: 지금까지 아는 사실이 모두 "새 사실"
        while any(delta.values()):
            rounds += 1
            if rounds > MAX_ROUNDS:
                raise DatalogError(f"{MAX_ROUNDS}회차가 넘도록 끝나지 않아요 (곱이 계속 커지는 규칙인지 확인)")
            new: dict[str, set[Fact]] = defaultdict(set)
            for rule in rules:
                pos, neg = rule.positive, rule.negative
                for k, atom in enumerate(pos):
                    if not delta.get(atom.pred):
                        continue
                    for binding in _join(pos, k, delta, total, negative=neg):
                        fact = _ground(rule.head, binding)
                        if fact not in total[rule.head.pred]:
                            new[rule.head.pred].add(fact)
            for pred, rows in new.items():
                total[pred] |= rows
            delta = new
    return Result(relations=dict(total), rounds=rounds, strata=len(strata) or 1)


def _fmt(atom: Atom) -> str:
    def term(t):
        if isinstance(t, Var):
            return "_" if t.name.startswith(ANON) else t.name
        if isinstance(t, Product):
            return " * ".join(term(f) for f in t.factors)
        return f'"{t}"' if isinstance(t, str) else str(t)
    return f"{'!' if atom.negated else ''}{atom.pred}({', '.join(term(a) for a in atom.args)})"
