"""Grade every turn of a random-battle replay (roadmap stage 6, vault ADR-0014).

For each turn start:
1. Candidates: each side's top-K choices by the policy, plus the choice actually played
   and the Tera version of the top move (mikumiku: top-8 x top-8).
2. Every pair is played on Showdown's simulator from the exact position (rebuilt from
   the inputlog), with S seeds for the dice. When a Pokemon faints mid-turn, the side
   that must replace it picks its best replacement.
3. Each result is scored by the value network (public view, both perspectives averaged).
4. The table is solved as a zero-sum game (regret matching, as PS Dashboard and
   mikumiku do). A choice's value = expected win chance against the opponent's
   equilibrium mix. Regret = best value - value of the choice played.
5. Verdicts on regret in win-probability points: inaccuracy 5, mistake 10, blunder 20
   (PS Dashboard); softened one tier when the side is already at 85%+; no blame on
   turns the Pokemon could not act (full paralysis, sleep, flinch...).
6. Luck = what actually happened minus what was expected after both choices.
"""
from __future__ import annotations

import copy
import math
import time
from typing import Callable

import numpy as np

from server.battle.parser import LogParser
from training.features import MOVES, N_SWITCH, SIZES, encode, turn_actions, turn_events

BANDS = [(20.0, "blunder"), (10.0, "mistake"), (5.0, "inaccuracy")]
SOFTEN = {"blunder": "mistake", "mistake": "inaccuracy", "inaccuracy": "good"}
WINNING = 0.85
ANALYSIS_VERSION = 1


# ---------------------------------------------------------------- helpers
def lichess_accuracy(loss_points: float) -> float:
    """Lichess's move accuracy from the win-percentage lost (0-100)."""
    a = 103.1668100711649 * math.exp(-0.04354415386753951 * loss_points) - 3.166924740191411
    return max(0.0, min(100.0, a))


def verdict(regret_points: float, value_before: float) -> str:
    v = "good"
    for limit, name in BANDS:
        if regret_points >= limit:
            v = name
            break
    if regret_points < 0.5:
        v = "best"
    if value_before >= WINNING and v in SOFTEN:
        v = SOFTEN[v]  # already winning comfortably: don't stack blunders in garbage time
    return v


def solve(M: np.ndarray, iters: int = 3000) -> tuple[np.ndarray, np.ndarray]:
    """Equilibrium mixes of a zero-sum matrix game (row player maximizes M) by
    regret matching+ with averaged strategies."""
    n, m = M.shape
    r1, r2 = np.zeros(n), np.zeros(m)
    s1, s2 = np.zeros(n), np.zeros(m)
    for t in range(1, iters + 1):
        x = r1 / r1.sum() if r1.sum() > 0 else np.full(n, 1 / n)
        y = r2 / r2.sum() if r2.sum() > 0 else np.full(m, 1 / m)
        u1 = M @ y
        u2 = 1 - x @ M
        r1 = np.maximum(r1 + u1 - x @ u1, 0)
        r2 = np.maximum(r2 + u2 - y @ u2, 0)
        s1 += t * x
        s2 += t * y
    return s1 / s1.sum(), s2 / s2.sum()


def label(choice: str, info: dict) -> str:
    parts = choice.split()
    if parts[0] == "move":
        i = int(parts[1]) - 1
        name = info["moves"][i]["name"] if i < len(info["moves"]) else choice
        return f"{name} + Tera {info['canTera']}" if "terastallize" in parts and info.get("canTera") else name
    if parts[0] == "switch":
        i = int(parts[1]) - 1
        return f"Switch to {info['team'][i]['species']}" if i < len(info["team"]) else choice
    return choice


class Model:
    """Thin wrapper over server.model_eval.ModelEval for batches of (state, side)."""

    def __init__(self, model_eval):
        self.m = model_eval
        self.t = model_eval.torch

    def run(self, items: list[tuple[dict, str, dict | None]]) -> tuple[np.ndarray, np.ndarray]:
        if not items:
            return np.zeros(0), np.zeros((0, SIZES["moves"] + N_SWITCH))
        enc = [encode(s, side, ev) for s, side, ev in items]
        t = self.t
        with t.no_grad():
            ids = t.from_numpy(np.stack([e[0] for e in enc]).astype(np.int64))
            mon = t.from_numpy(np.stack([e[1] for e in enc]))
            field = t.from_numpy(np.stack([e[2] for e in enc]))
            v, p = self.m.model(ids, mon, field)
            return t.sigmoid(v / self.m.temperature).numpy(), p.numpy()

    def value_p1(self, states: list[tuple[dict, dict | None]]) -> np.ndarray:
        """p1's win chance, averaging p1's view and 1 - p2's view."""
        items = [(s, "p1", ev) for s, ev in states] + [(s, "p2", ev) for s, ev in states]
        v, _ = self.run(items)
        n = len(states)
        return (v[:n] + 1 - v[n:]) / 2


# ---------------------------------------------------------------- main
def analyze(replay: dict, model_eval, engine, seeds: int = 16, top_k: int = 6,
            progress: Callable[[int, int], None] | None = None) -> dict:
    """Full move review of one replay (needs replay['inputlog'])."""
    model = Model(model_eval)
    log = replay["log"]
    lines = log.splitlines()
    real_events = turn_events(log)
    cant = turn_actions(log)

    # Parser copies at every turn start, from the real log.
    parser = LogParser()
    bases: dict[int, LogParser] = {}
    for line in lines:
        parser.feed(line)
        if line.startswith("|turn|"):
            t = parser.state.turn
            keep = parser.result.states
            parser.result.states = []
            bases[t] = copy.deepcopy(parser)
            parser.result.states = keep
    final = parser.state
    p1_name = final.sides["p1"].name

    loaded = engine.load(replay["inputlog"])
    turns = [t for t in loaded["turns"] if t["turn"] in bases]
    real_states = {t: bases[t].state.snapshot() for t in bases}

    # Win chance at every real turn start, and at the end.
    order = sorted(real_states)
    vals = model.value_p1([(real_states[t], real_events.get(t - 1) if t > 1 else None) for t in order])
    value_at = dict(zip(order, vals.tolist()))
    end_value = 1.0 if final.winner == p1_name else 0.0 if final.winner else 0.5

    out_turns = []
    t0 = time.time()
    for n, tinfo in enumerate(turns):
        turn = tinfo["turn"]
        state = real_states[turn]
        prev = real_events.get(turn - 1) if turn > 1 else None
        # 1. candidates from the policy
        _, pol = model.run([(state, "p1", prev), (state, "p2", prev)])
        cands = {}
        for k, side in enumerate(("p1", "p2")):
            opts = tinfo["options"][side]
            info = tinfo["info"][side]
            own = [m["name"] for m in state["sides"][side]["team"] if m["seen"]][:6]
            scored = []
            for o in opts:
                parts = o.split()
                if parts[0] == "move":
                    i = int(parts[1]) - 1
                    mid = info["moves"][i]["id"] if i < len(info["moves"]) else ""
                    idx = MOVES.get(mid)
                    s = float(pol[k, idx]) if idx is not None else -1e9
                    s -= 0.01 if "terastallize" in parts else 0.0
                else:
                    i = int(parts[1]) - 1
                    name = info["team"][i]["name"] if i < len(info["team"]) else ""
                    slot = own.index(name) if name in own else len(own)
                    s = float(pol[k, SIZES["moves"] + slot]) if slot < N_SWITCH else -1e9
                    s = s if math.isfinite(s) else -1e9
                scored.append((s, o))
            scored.sort(reverse=True)
            chosen = [o for _, o in scored if "terastallize" not in o][:top_k]
            tera = [o for _, o in scored if "terastallize" in o][:1]
            played = tinfo["played"].get(side)
            pick = list(dict.fromkeys(chosen + tera + ([played] if played in opts else [])))
            cands[side] = pick or opts[:1]
        c1, c2 = cands["p1"], cands["p2"]
        pairs = [(a, b) for a in c1 for b in c2]

        # 2. play every pair on the simulator
        cells = engine.expand(turn, pairs, seeds)
        base = bases[turn]
        leaf_items, leaf_index, exact = [], [], {}
        for ci, cell in enumerate(cells):
            for bi, br in enumerate(cell["branches"]):
                key = (ci, bi)
                if br["ended"]:
                    exact[key] = 1.0 if br["winner"] == p1_name else 0.0 if br["winner"] else 0.5
                    continue
                p = copy.deepcopy(base)
                for ln in br["lines"]:
                    p.feed(ln)
                ev = turn_events("\n".join(br["lines"])).get(0)
                leaf_items.append((p.state.snapshot(), ev))
                leaf_index.append(key)
        leaf_vals = dict(zip(leaf_index, model.value_p1(leaf_items).tolist())) if leaf_items else {}
        leaf_vals.update(exact)

        # 3. table of expected p1 win chance per pair (mean over seeds)
        sums = np.zeros((len(c1), len(c2)))
        counts = np.zeros((len(c1), len(c2)))
        for ci, cell in enumerate(cells):
            if cell["invalid"] or not cell["branches"]:
                continue
            i, j = divmod(cell["pair"], len(c2))
            vs = [leaf_vals[(ci, bi)] for bi in range(len(cell["branches"]))]
            chooser = cell["branches"][0]["switch"]["side"] if cell["branches"][0]["switch"] else None
            v = max(vs) if chooser == "p1" else min(vs) if chooser == "p2" else vs[0]
            sums[i, j] += v
            counts[i, j] += 1
        valid_rows = counts.sum(1) > 0
        valid_cols = counts.sum(0) > 0
        M = np.where(counts > 0, sums / np.maximum(counts, 1), 0.5)
        M = M[np.ix_(valid_rows, valid_cols)]
        c1v = [c for c, ok in zip(c1, valid_rows) if ok]
        c2v = [c for c, ok in zip(c2, valid_cols) if ok]
        if not c1v or not c2v:
            continue
        x, y = solve(M)
        q1 = M @ y               # p1's value of each choice vs p2's equilibrium mix
        q2 = 1 - x @ M           # p2's value of each choice vs p1's equilibrium mix
        eq = float(x @ M @ y)

        v_before = value_at[turn]
        nxt = [t for t in order if t > turn]
        v_after = value_at[nxt[0]] if nxt else end_value
        entry = {"turn": turn, "value_before": v_before, "value_after": v_after, "equilibrium": eq, "sides": {}}
        played1, played2 = tinfo["played"].get("p1"), tinfo["played"].get("p2")
        if played1 in c1v and played2 in c2v:
            expected = float(M[c1v.index(played1), c2v.index(played2)])
            entry["expected_after"] = expected
            entry["luck_p1"] = v_after - expected
        for side, cs, q, mix, played, mine in (("p1", c1v, q1, x, played1, v_before),
                                               ("p2", c2v, q2, y, played2, 1 - v_before)):
            info = tinfo["info"][side]
            best = int(np.argmax(q))
            rec = {
                "options": [{"choice": c, "label": label(c, info), "value": float(q[i]), "mix": float(mix[i])}
                            for i, c in sorted(enumerate(cs), key=lambda kv: -q[kv[0]])],
                "best": cs[best], "best_label": label(cs[best], info), "best_value": float(q[best]),
                "n_options": len(tinfo["options"][side]),
            }
            if played in cs:
                pv = float(q[cs.index(played)])
                regret = max(0.0, float(q[best]) - pv) * 100
                rec.update(played=played, played_label=label(played, info), played_value=pv, regret=regret,
                           verdict=verdict(regret, mine))
                if len(tinfo["options"][side]) <= 1:
                    rec["verdict"] = "forced"
                if cant.get(turn, {}).get(side, ("",))[0] == "none":
                    rec["verdict"] = "no blame"
                    rec["no_blame"] = "the Pokémon couldn't act this turn"
            entry["sides"][side] = rec
        out_turns.append(entry)
        if progress:
            progress(n + 1, len(turns))

    return {"version": ANALYSIS_VERSION, "seeds": seeds, "top_k": top_k, "turns": out_turns,
            "summary": summarize(out_turns, final), "seconds": round(time.time() - t0, 1),
            "players": {"p1": final.sides["p1"].name, "p2": final.sides["p2"].name}}


def summarize(turns: list[dict], final) -> dict:
    out = {}
    for side in ("p1", "p2"):
        graded = [t["sides"][side] for t in turns if side in t["sides"] and "regret" in t["sides"][side]
                  and t["sides"][side]["verdict"] not in ("forced", "no blame")]
        counts = {k: sum(1 for g in graded if g["verdict"] == k) for k in ("best", "good", "inaccuracy", "mistake", "blunder")}
        accs = [lichess_accuracy(g["regret"]) for g in graded]
        luck = sum((t.get("luck_p1", 0.0) if side == "p1" else -t.get("luck_p1", 0.0)) for t in turns)
        worst = sorted(((t["turn"], t["sides"][side]) for t in turns if side in t["sides"] and "regret" in t["sides"][side]
                        and t["sides"][side]["verdict"] in ("mistake", "blunder")), key=lambda kv: -kv[1]["regret"])[:3]
        out[side] = {
            "name": final.sides[side].name, "graded_turns": len(graded), "counts": counts,
            "accuracy": round(sum(accs) / len(accs), 1) if accs else None,
            "avg_regret": round(sum(g["regret"] for g in graded) / len(graded), 2) if graded else None,
            "luck_points": round(luck * 100, 1),
            "worst": [{"turn": t, "played": r["played_label"], "best": r["best_label"], "regret": round(r["regret"], 1)}
                      for t, r in worst],
        }
    swings = sorted(((t["turn"], t["luck_p1"]) for t in turns if "luck_p1" in t), key=lambda kv: -abs(kv[1]))[:3]
    out["biggest_luck"] = [{"turn": t, "luck_p1_points": round(l * 100, 1)} for t, l in swings]
    return out
