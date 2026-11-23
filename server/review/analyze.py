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

Two modes for step 2 (vault ADR-0015):
- "worlds" (default): each player is graded on what they could know. The opponent's
  unrevealed moves, item, ability and Tera type are sampled from the randbats set data
  (server/review/worlds.py); every world gets its own matrix (the opponent knows its own
  set and answers within it), and a choice's value is its average over worlds.
- "perfect": one shared matrix with the real hidden sets (hindsight; ADR-0014).
Luck is always measured in the real game: the played pair replayed with the real sets.
"""
from __future__ import annotations

import copy
import math
import time
from typing import Callable, Collection

import numpy as np

from server.battle.parser import LogParser
from server.review.worlds import sample_worlds
from training.features import MOVES, N_SWITCH, SIZES, encode, turn_actions, turn_events

BANDS = [(20.0, "blunder"), (10.0, "mistake"), (5.0, "inaccuracy")]
SOFTEN = {"blunder": "mistake", "mistake": "inaccuracy", "inaccuracy": "good"}
WINNING = 0.85
ANALYSIS_VERSION = 2


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


# ---------------------------------------------------------------- pieces
# Eval bar after a move review (vault plan-model-gains): blend the one-turn search with the
# network. On 199 future games (worlds mode) 75% search + 25% network beat the network by
# 0.0083 log-loss [-0.0118, -0.0048] (vault 2026-11-23-v12-tests-and-eval-gains-results).
SEARCH_BLEND = 0.75


def search_value_p1(entry: dict) -> float | None:
    """p1's chance from a turn's solved matrix: p1's best value and 1 - p2's best value
    (each against the other side's equilibrium answer), averaged."""
    vals = []
    for side in ("p1", "p2"):
        rec = (entry.get("sides") or {}).get(side)
        if rec and rec.get("best_value") is not None:
            vals.append(rec["best_value"] if side == "p1" else 1 - rec["best_value"])
    return float(np.mean(vals)) if vals else None


def other(side: str) -> str:
    return "p2" if side == "p1" else "p1"


def rank_options(pol_row: np.ndarray, opts: list[str], info: dict, own: list[str], top_k: int,
                 played: str | None = None) -> list[str]:
    """The top-K choices by the policy, plus the best Tera choice and the played one."""
    scored = []
    for o in opts:
        parts = o.split()
        if parts[0] == "move":
            i = int(parts[1]) - 1
            mid = info["moves"][i]["id"] if i < len(info["moves"]) else ""
            idx = MOVES.get(mid)
            s = float(pol_row[idx]) if idx is not None else -1e9
            s -= 0.01 if "terastallize" in parts else 0.0
        else:
            i = int(parts[1]) - 1
            name = info["team"][i]["name"] if i < len(info["team"]) else ""
            slot = own.index(name) if name in own else len(own)
            s = float(pol_row[SIZES["moves"] + slot]) if slot < N_SWITCH else -1e9
        scored.append((s if math.isfinite(s) else -1e9, o))
    scored.sort(reverse=True)
    chosen = [o for _, o in scored if "terastallize" not in o][:top_k]
    tera = [o for _, o in scored if "terastallize" in o][:1]
    pick = list(dict.fromkeys(chosen + tera + ([played] if played in opts else [])))
    return pick or opts[:1]


def cell_values(cells: list[dict], base: LogParser, model: Model, p1_name: str) -> list[float | None]:
    """p1's win chance after each simulated cell (None if the choices were invalid). When a
    side had to replace a fainted Pokemon, it gets its best replacement."""
    items, index, exact = [], [], {}
    for ci, cell in enumerate(cells):
        for bi, br in enumerate(cell["branches"]):
            if br["ended"]:
                exact[(ci, bi)] = 1.0 if br["winner"] == p1_name else 0.0 if br["winner"] else 0.5
                continue
            p = copy.deepcopy(base)
            for ln in br["lines"]:
                p.feed(ln)
            items.append((p.state.snapshot(), turn_events("\n".join(br["lines"])).get(0)))
            index.append((ci, bi))
    vals = dict(zip(index, model.value_p1(items).tolist())) if items else {}
    vals.update(exact)
    out: list[float | None] = []
    for ci, cell in enumerate(cells):
        if cell["invalid"] or not cell["branches"]:
            out.append(None)
            continue
        vs = [vals[(ci, bi)] for bi in range(len(cell["branches"]))]
        sw = cell["branches"][0]["switch"]
        out.append(max(vs) if sw and sw["side"] == "p1" else min(vs) if sw else vs[0])
    return out


def mean_matrix(entries: list[tuple[int, int, float | None]], n: int, m: int) -> np.ndarray:
    """Mean value per (row, col); NaN where no valid sample."""
    sums, counts = np.zeros((n, m)), np.zeros((n, m))
    for i, j, v in entries:
        if v is not None:
            sums[i, j] += v
            counts[i, j] += 1
    return np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)


def solve_valid(M: np.ndarray):
    """Solve on the rows and columns that have data. Returns (q per row, row mix, col mix,
    game value), with NaN q / zero mix for rows without data; None if nothing is valid."""
    rows = ~np.all(np.isnan(M), axis=1)
    cols = ~np.all(np.isnan(M), axis=0)
    if not rows.any() or not cols.any():
        return None
    sub = M[np.ix_(rows, cols)]
    sub = np.where(np.isnan(sub), np.nanmean(sub), sub)
    x, y = solve(sub)
    q = np.full(M.shape[0], np.nan)
    q[rows] = sub @ y
    xm = np.zeros(M.shape[0])
    xm[rows] = x
    ym = np.zeros(M.shape[1])
    ym[cols] = y
    return q, xm, ym, float(x @ sub @ y)


def side_record(cs: list[str], q: np.ndarray, mix: np.ndarray, played: str | None, info: dict,
                n_options: int, mine: float, couldnt_act: bool) -> dict | None:
    ok = [i for i in range(len(cs)) if not np.isnan(q[i])]
    if not ok:
        return None
    best = max(ok, key=lambda i: q[i])
    rec = {
        "options": [{"choice": cs[i], "label": label(cs[i], info), "value": float(q[i]), "mix": float(mix[i])}
                    for i in sorted(ok, key=lambda i: -q[i])],
        "best": cs[best], "best_label": label(cs[best], info), "best_value": float(q[best]),
        "n_options": n_options,
    }
    if played in cs and cs.index(played) in ok:
        pv = float(q[cs.index(played)])
        regret = max(0.0, float(q[best]) - pv) * 100
        rec.update(played=played, played_label=label(played, info), played_value=pv, regret=regret,
                   verdict=verdict(regret, mine))
        if n_options <= 1:
            rec["verdict"] = "forced"
        if couldnt_act:
            rec["verdict"] = "no blame"
            rec["no_blame"] = "the Pokémon couldn't act this turn"
    return rec


# ---------------------------------------------------------------- main
def analyze(replay: dict, model_eval, engine, seeds: int = 16, top_k: int = 6, mode: str = "worlds",
            progress: Callable[[int, int], None] | None = None, only_turns: Collection[int] | None = None,
            seed_offset: int = 0) -> dict:
    """Full move review of one replay (needs replay['inputlog']). In "worlds" mode `seeds`
    is the number of sampled worlds per graded side (each with its own dice).

    `only_turns` grades just those turns (the verdict bank's high-effort references);
    `seed_offset` (worlds mode) draws different worlds and dice, for an independent re-run."""
    if mode not in ("worlds", "perfect"):
        raise ValueError(f"unknown mode {mode}")
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
        if only_turns is not None and turn not in only_turns:
            continue
        state = real_states[turn]
        base = bases[turn]
        prev = real_events.get(turn - 1) if turn > 1 else None
        played = {s: tinfo["played"].get(s) for s in ("p1", "p2")}
        _, pol = model.run([(state, "p1", prev), (state, "p2", prev)])
        pol_of = {"p1": pol[0], "p2": pol[1]}
        own = {s: [m["name"] for m in state["sides"][s]["team"] if m["seen"]][:6] for s in ("p1", "p2")}
        cands = {s: rank_options(pol_of[s], tinfo["options"][s], tinfo["info"][s], own[s], top_k, played[s])
                 for s in ("p1", "p2")}
        v_before = value_at[turn]
        nxt = [t for t in order if t > turn]
        v_after = value_at[nxt[0]] if nxt else end_value
        mine = {"p1": v_before, "p2": 1 - v_before}
        couldnt = {s: cant.get(turn, {}).get(s, ("",))[0] == "none" for s in ("p1", "p2")}
        entry = {"turn": turn, "value_before": v_before, "value_after": v_after, "sides": {},
                 # Pokemon left per side (unseen ones count as alive): small endgames for the verdict bank
                 "alive": {sd: 6 - sum(1 for m in state["sides"][sd]["team"] if m["fainted"]) for sd in ("p1", "p2")}}

        if mode == "perfect":
            c1, c2 = cands["p1"], cands["p2"]
            cells = engine.expand(turn, [(a, b) for a in c1 for b in c2], seeds)
            cv = cell_values(cells, base, model, p1_name)
            M = mean_matrix([(*divmod(c["pair"], len(c2)), v) for c, v in zip(cells, cv)], len(c1), len(c2))
            sol = solve_valid(M)
            if sol is None:
                continue
            q1, x, y, eq = sol
            sol2 = solve_valid(1 - M.T)
            q2 = sol2[0] if sol2 else np.full(len(c2), np.nan)
            entry["equilibrium"] = eq
            if played["p1"] in c1 and played["p2"] in c2:
                e = M[c1.index(played["p1"]), c2.index(played["p2"])]
                if not np.isnan(e):
                    entry["expected_after"] = float(e)
                    entry["luck_p1"] = v_after - float(e)
            for side, cs, q, mix in (("p1", c1, q1, x), ("p2", c2, q2, y)):
                rec = side_record(cs, q, mix, played[side], tinfo["info"][side], len(tinfo["options"][side]),
                                  mine[side], couldnt[side])
                if rec:
                    entry["sides"][side] = rec
        else:
            # One batch of simulations: each side graded over its own worlds, plus the
            # played pair in the real game for luck.
            plan, all_jobs = {}, []
            for side in ("p1", "p2"):
                opp = other(side)
                worlds = sample_worlds(state, side, seeds, seed=turn * 2 + (side == "p2") + 100_003 * seed_offset)
                wopts = engine.options(turn, worlds)
                cols = []
                for k, (w, o) in enumerate(zip(worlds, wopts)):
                    cy = rank_options(pol_of[opp], o["options"][opp], o["info"][opp], own[opp], top_k)
                    cols.append(cy)
                    pairs = [(a, b) if side == "p1" else (b, a) for a in cands[side] for b in cy]
                    all_jobs.append({"world": w, "seed": k + 1000 * seed_offset, "pairs": pairs})
                plan[side] = (len(all_jobs) - len(worlds), cols)
            luck_job = None
            if played["p1"] in tinfo["options"]["p1"] and played["p2"] in tinfo["options"]["p2"]:
                luck_job = len(all_jobs)
                all_jobs += [{"world": None, "seed": k, "pairs": [(played["p1"], played["p2"])]} for k in range(seeds)]
            cells = engine.expand_jobs(turn, all_jobs)
            cv = cell_values(cells, base, model, p1_name)
            by_job: dict[int, list] = {}
            for c, v in zip(cells, cv):
                by_job.setdefault(c["job"], []).append((c["pair"], v))
            eqs = {}
            for side in ("p1", "p2"):
                first, cols = plan[side]
                cx = cands[side]
                qs, mixes, games = [], [], []
                for k, cy in enumerate(cols):
                    ents = []
                    for pi, v in by_job.get(first + k, []):
                        i, j = divmod(pi, len(cy))
                        ents.append((i, j, None if v is None else (v if side == "p1" else 1 - v)))
                    sol = solve_valid(mean_matrix(ents, len(cx), len(cy)))
                    if sol is None:
                        continue
                    qs.append(sol[0])
                    mixes.append(sol[1])
                    games.append(sol[3])
                if not qs:
                    continue
                with np.errstate(all="ignore"):
                    q = np.nanmean(np.stack(qs), axis=0)
                mix = np.mean(np.stack(mixes), axis=0)
                eqs[side] = float(np.mean(games))
                rec = side_record(cx, q, mix, played[side], tinfo["info"][side], len(tinfo["options"][side]),
                                  mine[side], couldnt[side])
                if rec:
                    rec["worlds"] = len(qs)
                    entry["sides"][side] = rec
            if "p1" in eqs:
                entry["equilibrium"] = eqs["p1"]
            if luck_job is not None:
                lv = [v for j in range(luck_job, luck_job + seeds) for _, v in by_job.get(j, []) if v is not None]
                if lv:
                    entry["expected_after"] = float(np.mean(lv))
                    entry["luck_p1"] = v_after - entry["expected_after"]
        if not entry["sides"]:
            continue
        out_turns.append(entry)
        if progress:
            progress(n + 1, len(turns))

    return {"version": ANALYSIS_VERSION, "mode": mode, "seeds": seeds, "top_k": top_k, "turns": out_turns,
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
