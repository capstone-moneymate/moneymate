"""1-5 실험 돌리기 (사람1, #238). 안 A: 카드 2장 × 학습자 4종류 × 반복 2번 = 칸마다 세션 16개.

칸(cell) = 설정 하나: 설정 이름, 교사(조건), 선수 효과, 학습자 배울 확률, 퀴즈 상한, 과거 기록, 학습자 실수, 확신 잡음
- main     선수 효과 1.0 / 0.5 / 0.0 마다 고정·규칙·에이전트. 확신 없음 (세 조건이 같은 정보로)
- ablation 선수 효과 0.5 에서 에이전트 제거 실험 no_bkt, no_prereq
- conf     선수 효과 0.5 에서 에이전트에 확신을 넣어 보기: 잡음 0 (숨긴 상태 그대로) / 0.4 (40% 반대). 확신 효과의 범위
- cap10    선수 효과 0.5, 퀴즈 상한 10 × 세 조건
- sens     학습자 배울 확률 0.1 / 0.5 × 선수 효과 셋, 고정·규칙만 (비용 0)
- slip     학습자 실수 0.05 / 0.2 / 0.3 × 선수 효과 셋, 고정·규칙만 (비용 0). BKT 는 실수 0.1 그대로
           ("시스템 가정과 실제 학습자가 달라도 결론이 유지되나". 실수는 학생마다 크게 다르다, Corbett & Anderson 1995)
과거 기록 없음(prior=False)은 고정·규칙만 main·cap10·sens.
BKT 값은 기본이 지금 앱의 값(learner.bkt.DEFAULT). --bkt 0.25,0.1,0.1 처럼 처음·배울·실수를 바꿔 돌릴 수 있다
(사람2 가 앱 값을 바꾸기 전에 미리 보기). 결과 줄에 BKT 값이 남아 칸이 섞이지 않는다.

에이전트 세션은 Opus 를 불러 비용이 든다 (2026-11-25 실측 세션 하나 약 $0.078, 에이전트 칸 8개 × 16 = 128 세션 약 $10).
결과는 세션마다 logs/eval/results.jsonl 에 한 줄씩 붙이고, 이미 있는 세션은 건너뛴다 (중간에 멈춰도 이어서).

    python -m eval.run                       # 비용 0: 고정·규칙만 (모든 설정)
    python -m eval.run --agent --limit 1     # 에이전트 세션 1개만 시험
    python -m eval.run --agent               # 전체
    python -m eval.run --bkt 0.25,0.1,0.1    # BKT 값을 바꿔서
    python -m eval.run --report              # 표·그래프만 다시
"""
import argparse
import json
import random
import statistics
import zlib
from pathlib import Path

from eval import bank as bk
from eval import teachers as te
from eval.learner import SLIP, Learner, prereq_of, profiles
from generate.llm_client import ROOT
from learner import bkt
from tutor import agent as ag

OUT = ROOT / "logs" / "eval"
RESULTS = OUT / "results.jsonl"
SEEDS = (0, 1)
EFFECTS = (1.0, 0.5, 0.0)
CELL_FIELDS = ("setting", "condition", "prereq_effect", "p_learn", "cap", "prior", "slip", "conf_noise")


def cell(setting, condition, effect, p_learn=0.3, cap=6, prior=True, slip=SLIP, conf_noise=None) -> dict:
    return {"setting": setting, "condition": condition, "prereq_effect": effect, "p_learn": p_learn, "cap": cap,
            "prior": prior, "slip": slip, "conf_noise": conf_noise}


def grid() -> list[dict]:
    out = []
    for prior in (True, False):
        conds = ("fixed", "rules", "agent") if prior else ("fixed", "rules")
        for e in EFFECTS:
            for c in conds:
                out.append(cell("main", c, e, prior=prior))
        for c in conds:
            out.append(cell("cap10", c, 0.5, cap=10, prior=prior))
        for pl in (0.1, 0.5):
            for e in EFFECTS:
                for c in ("fixed", "rules"):
                    out.append(cell("sens", c, e, p_learn=pl, prior=prior))
        if prior:
            for c in ("agent_no_bkt", "agent_no_prereq"):
                out.append(cell("ablation", c, 0.5))
            for noise in (0.0, 0.4):
                out.append(cell("conf", "agent", 0.5, conf_noise=noise))
            for sl in (0.05, 0.2, 0.3):
                for e in EFFECTS:
                    for c in ("fixed", "rules"):
                        out.append(cell("slip", c, e, slip=sl))
    return out


def bkt_tag(params: bkt.Params) -> str:
    return f"{params.p_init}/{params.p_learn}/{params.p_slip}"


def key(row) -> str:
    parts = [str(row[k]) for k in CELL_FIELDS] + [row["bkt"], str(row["card"]), row["profile"], str(row["seed"])]
    return "|".join(parts)


def done_keys(path: Path = RESULTS) -> set[str]:
    return {key(r) for r in load_rows(path)}


def run_one(cmap: ag.ConceptMap, card_bank: dict, card: int, profile: str, seed: int, c: dict,
            params: bkt.Params = bkt.DEFAULT) -> dict:
    targets, scope = card_bank["targets"], card_bank["scope"]
    edges = [e for e in cmap.edges if e[0] in scope and e[1] in scope]
    hidden = profiles(scope, targets, edges)[profile]
    # 같은 (카드, 학습자, 반복)이면 조건이 달라도 학습자의 무작위 흐름이 같은 씨앗에서 시작한다
    base = zlib.crc32(f"{card}|{profile}|{seed}".encode())   # hash() 는 실행마다 바뀌어서 쓰지 않는다
    learner = Learner(profile, set(hidden["known"]), set(hidden["wrong"]), prereq_of(edges), p_learn=c["p_learn"],
                      prereq_effect=c["prereq_effect"], slip=c["slip"], conf_noise=c["conf_noise"],
                      rng=random.Random(base))
    draw = bk.Draw(card_bank, random.Random(base + 1))
    row = {**c, "bkt": bkt_tag(params), "card": card, "profile": profile, "seed": seed}
    mastery = te.MemMastery(scope, blind=c["condition"] == "agent_no_bkt", params=params)
    if c["prior"]:
        row["prior_record"] = te.prior_record(card_bank, scope, learner, mastery, random.Random(base + 3))
    row["start_p"] = {k: round(v, 3) for k, v in mastery.p.items()}
    cond, cap = c["condition"], c["cap"]
    if cond == "fixed":
        ep = te.fixed(scope, targets, learner, draw, mastery, cap)
    elif cond == "rules":
        ep = te.rules(scope, targets, edges, learner, draw, mastery, cap)
    else:
        agent_map = cmap
        if cond == "agent_no_prereq":
            agent_map = ag.ConceptMap(cmap.labels, cmap.desc, [], cmap.confusable)
        ep, s = te.agent(agent_map, targets, learner, draw, mastery, cap, title=card_bank.get("title", ""))
        row["calls"] = s.calls
        row["log"] = [{"tool": e["tool"], "input": {k: v for k, v in e["input"].items() if k != "text"}} for e in s.log]
    right, total = te.final_test(card_bank["test"], targets, learner, random.Random(base + 2))
    row.update({"quizzes": ep.quizzes, "explains": ep.explains, "mastered_at": ep.mastered_at,
                "targets_known": sum(learner.knows(t) for t in targets), "n_targets": len(targets),
                "test_right": right, "test_total": total, "finished_by": ep.finished_by, "history": ep.history})
    return row


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in CELL_FIELDS) + (r["bkt"],), []).append(r)
    order = {"main": 0, "ablation": 1, "conf": 2, "cap10": 3, "sens": 4, "slip": 5}
    out = []
    for g, rs in sorted(groups.items(), key=lambda x: (x[0][-1], not x[0][5], order.get(x[0][0], 9), -x[0][2],
                                                       x[0][3], x[0][6], str(x[0][7]), x[0][1])):
        mastered = [r["mastered_at"] for r in rs if r["mastered_at"] is not None]
        out.append({
            **dict(zip(CELL_FIELDS, g[:-1])), "bkt": g[-1], "n": len(rs),
            "test_acc": round(sum(r["test_right"] for r in rs) / max(1, sum(r["test_total"] for r in rs)), 3),
            "targets_known": round(statistics.mean(r["targets_known"] / r["n_targets"] for r in rs), 3),
            "mastered_rate": round(len(mastered) / len(rs), 3),
            "quizzes": round(statistics.mean(r["quizzes"] for r in rs), 2),
            "mastered_at": round(statistics.mean(mastered), 2) if mastered else None,
        })
    return out


def report(rows: list[dict], out_dir: Path = OUT) -> Path:
    table = summarize(rows)
    lines = ["| BKT(처음/배움/실수) | 과거 기록 | 설정 | 조건 | 선수 효과 | 학습자 배울 | 학습자 실수 | 확신 잡음 | 상한 | 세션 | "
             "마지막 시험 정답률 | 목표 개념 앎 비율 | 목표 다 앎 | 낸 퀴즈 | 다 알기까지 퀴즈 |",
             "| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for t in table:
        noise = "-" if t["conf_noise"] is None else t["conf_noise"]
        lines.append(f"| {t['bkt']} | {'있음' if t['prior'] else '없음'} | {t['setting']} | {t['condition']} | {t['prereq_effect']} | "
                     f"{t['p_learn']} | {t['slip']} | {noise} | {t['cap']} | {t['n']} | {t['test_acc']:.0%} | "
                     f"{t['targets_known']:.0%} | {t['mastered_rate']:.0%} | {t['quizzes']} | "
                     f"{t['mastered_at'] if t['mastered_at'] is not None else '-'} |")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    _graph(table, out_dir / "summary.png")
    return path


def _graph(table: list[dict], path: Path) -> None:
    """main 설정(과거 기록 있음, 앱의 BKT 값): 선수 효과마다 조건별 목표 개념 앎 비율 막대."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    main = [t for t in table if t["setting"] == "main" and t["prior"] and t["bkt"] == bkt_tag(bkt.DEFAULT)]
    conds = [c for c in ("fixed", "rules", "agent") if any(t["condition"] == c for t in main)]
    if not conds:
        return
    plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "NanumGothic", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.8 / len(conds)
    for i, c in enumerate(conds):
        ys = [next((t["targets_known"] for t in main if t["condition"] == c and t["prereq_effect"] == e), 0) for e in EFFECTS]
        ax.bar([x + i * width for x in range(len(EFFECTS))], ys, width, label=c)
    ax.set_xticks([x + width * (len(conds) - 1) / 2 for x in range(len(EFFECTS))])
    ax.set_xticklabels([f"선수 효과 {e}" for e in EFFECTS])
    ax.set_ylim(0, 1)
    ax.set_ylabel("세션 끝 목표 개념 앎 비율 (숨긴 상태)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def load_rows(path: Path = RESULTS) -> list[dict]:
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if "bkt" in r]   # 확신·BKT 값을 기록하기 전의 옛 줄은 쓰지 않는다


def parse_bkt(text: str | None) -> bkt.Params:
    if not text:
        return bkt.DEFAULT
    p_init, p_learn, p_slip = (float(x) for x in text.split(","))
    return bkt.Params(p_init=p_init, p_learn=p_learn, p_slip=p_slip)


def main() -> None:
    p = argparse.ArgumentParser(description="1-5 가상 학습자 평가")
    p.add_argument("--agent", action="store_true", help="에이전트 칸도 돌린다 (Opus 비용)")
    p.add_argument("--limit", type=int, help="새로 돌릴 에이전트 세션 수 상한 (시험용)")
    p.add_argument("--bkt", help="BKT 처음,배울,실수 (예 0.25,0.1,0.1). 비우면 지금 앱의 값")
    p.add_argument("--report", action="store_true", help="표·그래프만 다시 만든다")
    args = p.parse_args()
    if args.report:
        print(f"표: {report(load_rows())}")
        return
    params = parse_bkt(args.bkt)
    from db import get_conn

    bank = bk.load()
    with get_conn() as conn:
        cmap = ag.ConceptMap.from_db(conn)
        titles = {cid: t for cid, t in conn.execute("SELECT id, title FROM cards WHERE id = ANY(%s)",
                                                        ([int(c) for c in bank["cards"]],)).fetchall()}
        conn.rollback()
    done = done_keys()
    OUT.mkdir(parents=True, exist_ok=True)
    agent_runs = 0
    with open(RESULTS, "a", encoding="utf-8") as f:
        for c in grid():
            is_agent = c["condition"].startswith("agent")
            if is_agent and not args.agent:
                continue
            for card_s, cb in bank["cards"].items():
                cb = {**cb, "title": titles.get(int(card_s), "")}
                for profile in profiles(cb["scope"], cb["targets"], []):
                    for seed in SEEDS:
                        probe = {**c, "bkt": bkt_tag(params), "card": int(card_s), "profile": profile, "seed": seed}
                        if key(probe) in done:
                            continue
                        if is_agent:
                            if args.limit is not None and agent_runs >= args.limit:
                                continue
                            agent_runs += 1
                        r = run_one(cmap, cb, int(card_s), profile, seed, c, params)
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        f.flush()
                        if is_agent:
                            print(f"   [{agent_runs}] {c['setting']} {c['condition']} 효과 {c['prereq_effect']} 카드 {card_s} "
                                  f"{profile} {seed}: 퀴즈 {r['quizzes']} 목표 앎 {r['targets_known']}/{r['n_targets']} "
                                  f"끝 {r['finished_by']}")
    print(f"표: {report(load_rows())}")


if __name__ == "__main__":
    main()
