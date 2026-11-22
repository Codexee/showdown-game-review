"""Build training arrays from replay logs (vault spec-eval-model).

    uv run python -m training.build_dataset --name small --hf data/hf/gen9randombattle_part11.parquet
    uv run python -m training.build_dataset --name full --hf 'data/hf/*.parquet' --since 2026-03-01
    uv run python -m training.build_dataset --name test --inputlog data/train/inputlog --both-sides

Output in data/train/ds/<name>/: raw little-endian arrays plus meta.json
  ids [N,13,8] int16 · mon [N,13,N_MON] float16 · field [N,N_FIELD] float16
  value [N] int8 · policy [N] int16 (-1 = none) · game [N] int32 · split [N] int8 (0 train, 1 val)
Games are split by a hash of their id, so a game's turns never land in both splits.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import multiprocessing as mp
import re
import time
from pathlib import Path

import numpy as np

from server.config import ROOT
from training.features import N_FIELD, N_IDS, N_MON, N_SET, N_TOKENS, game_samples

MAIN_ID = re.compile(r"^gen9randombattle-\d+$")
FIELDS = {
    "ids": (np.int16, (N_TOKENS, N_IDS)),
    "mon": (np.float16, (N_TOKENS, N_MON)),
    "field": (np.float16, (N_FIELD,)),
    "value": (np.int8, ()),
    "policy": (np.int16, ()),
    "opp_policy": (np.int16, ()),         # the opponent's choice that turn (auxiliary target)
    "opp_set": (np.int16, (6, N_SET)),    # opponent's item/ability/tera/moves revealed by game end (aux)
    "rating": (np.int16, ()),             # the replay's rating (0 = unrated), for the high-rating slice
    "game": (np.int32, ()),
    "split": (np.int8, ()),
}


def is_val(game_id: str, val_frac: float) -> bool:
    h = int(hashlib.blake2b(game_id.encode(), digest_size=4).hexdigest(), 16)
    return h / 2**32 < val_frac


def _work(task):
    gid_index, game_id, log, rating, both, val_frac = task
    rng = np.random.default_rng(gid_index)
    rows = []
    try:
        for row in game_samples(log, rng, both_sides=both):
            rows.append(row)
    except Exception:
        return gid_index, game_id, None
    if not rows:
        return gid_index, game_id, None
    split = 1 if is_val(game_id, val_frac) else 0
    out = {
        "ids": np.stack([r[0] for r in rows]).astype(np.int16),
        "mon": np.stack([r[1] for r in rows]).astype(np.float16),
        "field": np.stack([r[2] for r in rows]).astype(np.float16),
        "value": np.array([r[3] for r in rows], dtype=np.int8),
        "policy": np.array([r[4] for r in rows], dtype=np.int16),
        "opp_policy": np.array([r[5] for r in rows], dtype=np.int16),
        "opp_set": np.stack([r[6] for r in rows]).astype(np.int16),
        "rating": np.full(len(rows), rating, dtype=np.int16),
        "game": np.full(len(rows), gid_index, dtype=np.int32),
        "split": np.full(len(rows), split, dtype=np.int8),
    }
    return gid_index, game_id, out


def iter_hf(pattern: str, since: int, max_games: int):
    import pyarrow.parquet as pq
    n = 0
    for f in sorted(glob.glob(pattern)):
        pf = pq.ParquetFile(f)
        for rg in range(pf.metadata.num_row_groups):
            t = pf.read_row_group(rg, columns=["id", "log", "uploadtime", "rating"])
            for gid, log, ut, rating in zip(t.column("id").to_pylist(), t.column("log").to_pylist(),
                                            t.column("uploadtime").to_pylist(), t.column("rating").to_pylist()):
                if not MAIN_ID.match(gid or "") or int(ut or 0) < since or not log:
                    continue
                yield gid, log, _rating(rating)
                n += 1
                if max_games and n >= max_games:
                    return


def iter_inputlog(folder: Path, max_games: int):
    files = [p for p in sorted(folder.glob("*.json")) if not p.name.startswith("_")]  # _state.json: collector
    for n, p in enumerate(files):
        if max_games and n >= max_games:
            return
        d = json.loads(p.read_text())
        yield d["id"], d["log"], _rating(d.get("rating"))


def _rating(r) -> int:
    try:
        return max(0, min(int(float(r)), 32000))
    except (TypeError, ValueError):
        return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--hf", help="glob of HF parquet files")
    ap.add_argument("--inputlog", type=Path, help="folder of collected replay .json files")
    ap.add_argument("--since", default="2000-01-01", help="only games uploaded on/after this date (UTC)")
    ap.add_argument("--max-games", type=int, default=0)
    ap.add_argument("--both-sides", action="store_true", help="one sample per side per turn (default: one random side)")
    ap.add_argument("--val-frac", type=float, default=0.02)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 2))
    args = ap.parse_args()

    since = int(dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.UTC).timestamp())
    out_dir = ROOT / "data" / "train" / "ds" / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {k: open(out_dir / f"{k}.bin", "wb") for k in FIELDS}
    source = iter_hf(args.hf, since, args.max_games) if args.hf else iter_inputlog(args.inputlog, args.max_games)
    tasks = ((i, gid, log, rating, args.both_sides, args.val_frac) for i, (gid, log, rating) in enumerate(source))

    n = games = skipped = 0
    game_ids: list[str] = []
    t0 = time.time()
    with mp.Pool(args.workers) as pool:
        for gid_index, game_id, out in pool.imap(_work, tasks, chunksize=64):
            while len(game_ids) <= gid_index:
                game_ids.append("")
            game_ids[gid_index] = game_id
            if out is None:
                skipped += 1
                continue
            for k, f in files.items():
                f.write(np.ascontiguousarray(out[k]).tobytes())
            n += len(out["value"])
            games += 1
            if games % 20000 == 0:
                print(f"{games} games, {n} samples, {time.time() - t0:.0f} s", flush=True)
    for f in files.values():
        f.close()
    meta = {"n": n, "games": games, "skipped": skipped, "fields": {k: [np.dtype(t).name, list(s)] for k, (t, s) in FIELDS.items()},
            "source": args.hf or str(args.inputlog), "since": args.since, "both_sides": args.both_sides,
            "val_frac": args.val_frac, "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    (out_dir / "game_ids.json").write_text(json.dumps(game_ids))
    print(f"done: {games} games ({skipped} skipped), {n} samples in {time.time() - t0:.0f} s -> {out_dir}", flush=True)


def load(name: str) -> dict[str, np.ndarray]:
    """Memory-mapped arrays of a built dataset."""
    d = ROOT / "data" / "train" / "ds" / name
    meta = json.loads((d / "meta.json").read_text())
    n = meta["n"]
    return {k: np.memmap(d / f"{k}.bin", dtype=np.dtype(t), mode="r", shape=(n, *s))
            for k, (t, s) in meta["fields"].items()}


if __name__ == "__main__":
    main()
