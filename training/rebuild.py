"""Rebuild collected inputlog replays to full information (vault ADR-0009).

    uv run python -m training.rebuild

For each Showdown commit named in the replays' `>version` lines: make a git worktree
of smogon/pokemon-showdown at exactly that commit (one blobless clone, data/sim/),
build it, then run tools/sim-states.cjs on that commit's replays. Output, one gzip
JSON line per replay with `match` (rebuilt log equals the replay's public log) and the
true state at every turn: data/train/truth/<sha10>.jsonl.gz. Never rebuilds at a
different commit: a near commit can silently produce wrong hidden sets.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import subprocess
from pathlib import Path

from server.config import ROOT

SIM = ROOT / "data" / "sim"
REPO = SIM / "ps-repo"
TOOL = ROOT / "tools" / "sim-states.cjs"
BATCH = 200


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def checkout(sha: str) -> Path:
    """Built Showdown at exactly `sha` (full hash)."""
    target = SIM / "ps" / sha[:10]
    if (target / "dist" / "sim" / "battle-stream.js").exists():
        return target
    SIM.mkdir(parents=True, exist_ok=True)
    if not REPO.exists():
        run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
             "https://github.com/smogon/pokemon-showdown.git", str(REPO)])
    run(["git", "fetch", "-q", "origin", sha], cwd=REPO)
    if not target.exists():
        run(["git", "worktree", "add", "-q", "--detach", str(target), sha], cwd=REPO)
    run(["npm", "install", "--omit=dev", "--no-audit", "--no-fund", "--loglevel=error"], cwd=target)
    run(["node", "build"], cwd=target)
    return target


def version_of(path: Path) -> str | None:
    with open(path) as f:
        data = json.load(f)
    first = (data.get("inputlog") or "").split("\n", 1)[0]
    return first.split()[1] if first.startswith(">version ") and len(first.split()) > 1 else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=ROOT / "data" / "train" / "inputlog")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "train" / "truth")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    by_version: dict[str, list[Path]] = collections.defaultdict(list)
    for p in sorted(args.src.glob("*.json")):
        v = version_of(p)
        if v:
            by_version[v].append(p)
    print({v[:10]: len(ps) for v, ps in by_version.items()}, flush=True)

    totals = collections.Counter()
    for sha, paths in sorted(by_version.items(), key=lambda kv: -len(kv[1])):
        out_file = args.out / f"{sha[:10]}.jsonl.gz"
        done = set()
        if out_file.exists():
            with gzip.open(out_file, "rt") as f:
                done = {json.loads(line)["id"] for line in f}
        todo = [p for p in paths if p.stem not in done]
        if not todo:
            continue
        sim = checkout(sha)
        with gzip.open(out_file, "at") as out:
            for i in range(0, len(todo), BATCH):
                lines = run(["node", str(TOOL), str(sim), *map(str, todo[i:i + BATCH])]).splitlines()
                for line in lines:
                    rec = json.loads(line)
                    totals["match" if rec.get("match") else "mismatch" if "error" not in rec else "error"] += 1
                    out.write(line + "\n")
        print(f"{sha[:10]}: {len(todo)} rebuilt; running totals {dict(totals)}", flush=True)
    print(f"done: {dict(totals)}", flush=True)


if __name__ == "__main__":
    main()
