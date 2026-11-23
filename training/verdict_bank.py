"""Verdict bank: measure how right the move review's verdicts are (vault plan-grade-quality, step 1).

    uv run python -m training.verdict_bank grade  --games 60 --workers 8   # default review of future games
    uv run python -m training.verdict_bank pick   --size 70                # choose the bank's choices
    uv run python -m training.verdict_bank ref    --workers 8              # high-effort reference verdicts
    uv run python -m training.verdict_bank noise  --workers 8              # default effort, independent seeds
    uv run python -m training.verdict_bank report

Everything lives in data/verdict_bank/ and every step resumes. The reference is the same method
(depth 1, sampled worlds) with more effort: every legal choice (top 13) and 64 worlds per
side. It measures sampling noise and candidate pruning, not the method's own biases (dice
inside one world, one strategy across worlds, depth); those need exact endgames or human
labels (plan step 1 sources a and b).
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import time
from pathlib import Path

import numpy as np

from server.config import ROOT

PINNED = ROOT / "data" / "train" / "test_pinned"
OUT = ROOT / "data" / "verdict_bank"
DEFAULT = dict(seeds=16, top_k=6)
REFERENCE = dict(seeds=64, top_k=13)
FLAG = {"inaccuracy", "mistake", "blunder"}
BANDS = (5.0, 10.0, 20.0)


def _run(args: tuple[str, str, dict, list[int] | None, int]) -> dict:
    path, tag, effort, turns, offset = args
    from server import model_eval
    from server.review.analyze import analyze
    from server.review.engine import ReviewEngine, sim_for

    d = json.loads(Path(path).read_text())
    try:
        model = model_eval.load(ROOT / "data")
        t0 = time.time()
        with ReviewEngine(sim_for(d["inputlog"])) as engine:
            res = analyze({"log": d["log"], "inputlog": d["inputlog"]}, model, engine, mode="worlds",
                          only_turns=set(turns) if turns is not None else None, seed_offset=offset, **effort)
        res.update(game=Path(path).stem, seconds=round(time.time() - t0, 1), model=f"{model.info.get('run')}@{model.info.get('step')}")
        return res
    except Exception as e:  # one bad game must not stop the batch
        return {"game": Path(path).stem, "error": f"{type(e).__name__}: {e}"[:400]}


def _batch(tag: str, jobs: list[tuple], workers: int) -> None:
    folder = OUT / tag
    folder.mkdir(parents=True, exist_ok=True)
    todo = [j for j in jobs if not (folder / f"{Path(j[0]).stem}.json").exists()]
    print(f"{tag}: {len(jobs) - len(todo)} done, {len(todo)} to go", flush=True)
    with mp.get_context("spawn").Pool(workers) as pool:
        for i, r in enumerate(pool.imap_unordered(_run, todo)):
            (folder / f"{r['game']}.json").write_text(json.dumps(r))
            print(f"{tag} {i + 1}/{len(todo)} {r['game']} " + (f"ERROR {r['error'][:100]}" if "error" in r else f"{r['seconds']} s"), flush=True)


def _games(n: int, seed: int) -> list[Path]:
    files = sorted(PINNED.glob("*.json"))
    random.Random(seed).shuffle(files)
    out = []
    for f in files:
        il = json.loads(f.read_text()).get("inputlog") or ""
        if "@@@" not in il[:400]:          # custom-rule games are unsupported
            out.append(f)
        if len(out) >= n:
            break
    return out


def grade(args) -> None:
    _batch("default", [(str(f), "default", DEFAULT, None, 0) for f in _games(args.games, args.seed)], args.workers)


def _choices(res: dict):
    """(turn, side, record) for every graded choice of one review."""
    for t in res.get("turns", []):
        for side, r in (t.get("sides") or {}).items():
            if r and r.get("played") and r.get("verdict") and r.get("regret") is not None:
                yield t, side, r


def pick(args) -> None:
    rng = random.Random(args.seed)
    pool: dict[str, list] = {k: [] for k in ("flagged", "close", "switch", "tera", "endgame", "good")}
    for f in sorted((OUT / "default").glob("*.json")):
        res = json.loads(f.read_text())
        if "error" in res:
            continue
        for t, side, r in _choices(res):
            if r["verdict"] in ("forced", "no blame"):
                continue
            item = {"game": res["game"], "turn": t["turn"], "side": side, "played": r["played"],
                    "default_regret": r["regret"], "default_verdict": r["verdict"]}
            reg = r["regret"]
            if r["verdict"] in FLAG:
                pool["flagged"].append(item)
            if any(abs(reg - b) <= 1.0 for b in BANDS):
                pool["close"].append(item)
            if r["played"].startswith("switch"):
                pool["switch"].append(item)
            if "terastallize" in r["played"]:
                pool["tera"].append(item)
            if t.get("alive") and max(t["alive"].values()) <= 3:
                pool["endgame"].append(item)
            if r["verdict"] in ("best", "good"):
                pool["good"].append(item)
    quota = {"flagged": 0.30, "close": 0.20, "switch": 0.15, "tera": 0.10, "endgame": 0.10, "good": 0.15}
    bank, seen = [], set()
    for cat, share in quota.items():
        items = pool[cat][:]
        rng.shuffle(items)
        want = round(args.size * share)
        for it in items:
            key = (it["game"], it["turn"], it["side"])
            if key in seen:
                continue
            seen.add(key)
            bank.append({**it, "category": cat})
            want -= 1
            if want <= 0:
                break
    (OUT / "bank.json").write_text(json.dumps(bank, indent=1))
    print(f"bank: {len(bank)} choices from {len({b['game'] for b in bank})} games:",
          {c: sum(b['category'] == c for b in bank) for c in quota}, "| pool sizes:", {k: len(v) for k, v in pool.items()})


def _bank_jobs(tag: str, effort: dict, offset: int) -> list[tuple]:
    bank = json.loads((OUT / "bank.json").read_text())
    by_game: dict[str, set[int]] = {}
    for b in bank:
        by_game.setdefault(b["game"], set()).add(b["turn"])
    return [(str(PINNED / f"{g}.json"), tag, effort, sorted(ts), offset) for g, ts in sorted(by_game.items())]


def ref(args) -> None:
    effort = dict(seeds=args.seeds or REFERENCE["seeds"], top_k=args.top_k or REFERENCE["top_k"])
    _batch("reference", _bank_jobs("reference", effort, 0), args.workers)


def noise(args) -> None:
    _batch("noise", _bank_jobs("noise", DEFAULT, 1), args.workers)


def _lookup(tag: str) -> dict[tuple, dict]:
    out = {}
    for f in (OUT / tag).glob("*.json"):
        res = json.loads(f.read_text())
        for t, side, r in _choices(res) if "error" not in res else []:
            out[(res["game"], t["turn"], side)] = r
    return out


def _compare(bank: list[dict], a: dict, b: dict, label: str) -> dict:
    rows = [(x, a.get((x["game"], x["turn"], x["side"])), b.get((x["game"], x["turn"], x["side"]))) for x in bank]
    rows = [(x, ra, rb) for x, ra, rb in rows if ra and rb]
    if not rows:
        return {"label": label, "n": 0}
    flag = lambda r: r["verdict"] in FLAG
    same_flag = np.mean([flag(ra) == flag(rb) for _, ra, rb in rows])
    same_band = np.mean([ra["verdict"] == rb["verdict"] or (not flag(ra) and not flag(rb)) for _, ra, rb in rows])
    diff = np.array([abs(ra["regret"] - rb["regret"]) for _, ra, rb in rows])
    best_same = np.mean([ra.get("best") == rb.get("best") for _, ra, rb in rows])
    a_flag_b_not = sum(flag(ra) and not flag(rb) for _, ra, rb in rows)
    b_flag_a_not = sum(flag(rb) and not flag(ra) for _, ra, rb in rows)
    by_cat = {}
    for cat in sorted({x["category"] for x, _, _ in rows}):
        sub = [(x, ra, rb) for x, ra, rb in rows if x["category"] == cat]
        by_cat[cat] = {"n": len(sub), "same_flag": round(float(np.mean([flag(ra) == flag(rb) for _, ra, rb in sub])), 3),
                       "mean_regret_diff": round(float(np.mean([abs(ra["regret"] - rb["regret"]) for _, ra, rb in sub])), 2)}
    return {"label": label, "n": len(rows), "same_flag": round(float(same_flag), 3), "same_band": round(float(same_band), 3),
            "same_best_choice": round(float(best_same), 3), "mean_regret_diff": round(float(diff.mean()), 2),
            "max_regret_diff": round(float(diff.max()), 2), "flagged_only_by_first": int(a_flag_b_not),
            "flagged_only_by_second": int(b_flag_a_not), "by_category": by_cat}


def report(args) -> None:
    bank = json.loads((OUT / "bank.json").read_text())
    d, r, n = _lookup("default"), _lookup("reference"), _lookup("noise")
    out = {"bank": len(bank), "default_vs_reference": _compare(bank, d, r, "default (16 worlds, top 6) vs reference (64, top 13)"),
           "default_vs_rerun": _compare(bank, d, n, "default vs default with independent seeds")}
    secs = [json.loads(f.read_text()).get("seconds") for f in (OUT / "default").glob("*.json")]
    out["default_seconds_per_game"] = round(float(np.mean([s for s in secs if s])), 1) if secs else None
    (OUT / "report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grade"); g.add_argument("--games", type=int, default=60)
    p = sub.add_parser("pick"); p.add_argument("--size", type=int, default=70)
    r = sub.add_parser("ref"); r.add_argument("--seeds", type=int, default=0); r.add_argument("--top-k", type=int, default=0)
    sub.add_parser("noise"); sub.add_parser("report")
    for s in (g, p):
        s.add_argument("--seed", type=int, default=0)
    for s in sub.choices.values():
        s.add_argument("--workers", type=int, default=8)
        s.add_argument("--out", default="")
    args = ap.parse_args()
    global OUT
    if args.out:
        OUT = Path(args.out)
    {"grade": grade, "pick": pick, "ref": ref, "noise": noise, "report": report}[args.cmd](args)


if __name__ == "__main__":
    main()
