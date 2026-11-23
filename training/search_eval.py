"""Does a one-turn search predict the winner better than the raw network? (vault
plan-model-gains, candidate 4.)

For a random sample of pinned-bank games, runs the move review (server/review/analyze.py)
and keeps, for each turn, the network's two-view win chance at the turn start
(`value_before`) and the search value: each side's best choice valued against the other
side's equilibrium answer (`best_value`), averaged over the two sides as p1's chance.

    uv run python -m training.search_eval --games 120 --workers 4 --mode perfect
    uv run python -m training.search_eval --report

Results: data/models/search_eval/<mode>.jsonl (one game per line; resumable).
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import re
import time
from pathlib import Path

import numpy as np

from server.config import ROOT

BANK = ROOT / "data" / "train" / "test_pinned"
OUT = ROOT / "data" / "models" / "search_eval"


def winner_p1(log: str) -> float | None:
    names = dict(re.findall(r"^\|player\|(p[12])\|([^|]*)\|", log, re.M))
    m = re.search(r"^\|win\|(.*)$", log, re.M)
    if not m or "p1" not in names:
        return None
    return 1.0 if m.group(1).strip() == names["p1"] else 0.0


def search_p1(entry: dict) -> float | None:
    """p1's chance from the solved matrix: p1's best value and 1 - p2's best value, averaged."""
    vals = []
    for side in ("p1", "p2"):
        rec = (entry.get("sides") or {}).get(side)
        if rec and rec.get("best_value") is not None:
            vals.append(rec["best_value"] if side == "p1" else 1 - rec["best_value"])
    return float(np.mean(vals)) if vals else None


def one_game(args: tuple[str, str, int, int]) -> dict:
    path, mode, seeds, top_k = args
    from server import model_eval
    from server.review.analyze import analyze
    from server.review.engine import ReviewEngine, sim_for

    d = json.loads(Path(path).read_text())
    label = winner_p1(d["log"])
    model = model_eval.load(ROOT / "data")
    t0 = time.time()
    with ReviewEngine(sim_for(d["inputlog"])) as engine:
        res = analyze({"log": d["log"], "inputlog": d["inputlog"]}, model, engine, seeds=seeds, top_k=top_k, mode=mode)
    turns = [{"turn": e["turn"], "net": e.get("value_before"), "search": search_p1(e)} for e in res.get("turns", [])]
    return {"game": Path(path).stem, "label_p1": label, "mode": mode, "seconds": round(time.time() - t0, 1),
            "model": model.info.get("run"), "step": model.info.get("step"), "turns": turns}


def run(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{args.mode}.jsonl"
    done = {json.loads(l)["game"] for l in out.read_text().splitlines()} if out.exists() else set()
    files = sorted(BANK.glob("*.json"))
    random.Random(args.seed).shuffle(files)
    todo = [str(f) for f in files[:args.games] if f.stem not in done]
    print(f"{args.mode}: {len(done)} done, {len(todo)} to go", flush=True)
    with mp.get_context("spawn").Pool(args.workers) as pool, out.open("a") as fh:
        for i, r in enumerate(pool.imap_unordered(one_game, [(f, args.mode, args.seeds, args.top_k) for f in todo])):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(f"{i + 1}/{len(todo)} {r['game']} {r['seconds']} s", flush=True)


def report() -> None:
    from training.metrics import _ll, bootstrap

    for f in sorted(OUT.glob("*.jsonl")):
        rows = [json.loads(l) for l in f.read_text().splitlines()]
        y, net, srch, g = [], [], [], []
        for gi, r in enumerate(rows):
            if r["label_p1"] is None:
                continue
            for t in r["turns"]:
                if t["net"] is None or t["search"] is None:
                    continue
                y.append(r["label_p1"]); net.append(t["net"]); srch.append(t["search"]); g.append(gi)
        y, net, srch, g = map(np.asarray, (y, net, srch, g))
        if not len(y):
            continue
        d = _ll(srch, y) - _ll(net, y)
        ci = bootstrap(lambda w: float((d * w).sum() / w.sum()), g, 1000)
        acc = lambda p: float(((p > 0.5) == (y > 0.5)).mean())
        print(f"{f.stem}: {len(rows)} games, {len(y)} turns | network ll {_ll(net, y).mean():.4f} acc {acc(net):.3f} | "
              f"search ll {_ll(srch, y).mean():.4f} acc {acc(srch):.3f} | search - network {d.mean():+.4f} "
              f"[{ci[0]:+.4f}, {ci[1]:+.4f}] | {np.mean([r['seconds'] for r in rows]):.0f} s/game")
        for lam in (0.25, 0.5, 0.75):
            mix = lam * srch + (1 - lam) * net
            dm = _ll(mix, y) - _ll(net, y)
            cim = bootstrap(lambda w: float((dm * w).sum() / w.sum()), g, 1000)
            print(f"   blend {lam:.2f} search: ll {_ll(mix, y).mean():.4f} vs network {dm.mean():+.4f} [{cim[0]:+.4f}, {cim[1]:+.4f}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=120)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mode", choices=["perfect", "worlds"], default="perfect")
    ap.add_argument("--seeds", type=int, default=16)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    report() if args.report else run(args)


if __name__ == "__main__":
    main()
