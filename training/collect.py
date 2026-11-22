"""Collect recent public gen9randombattle replays WITH inputlogs from Showdown's API.

    uv run python -m training.collect --days 14

These are the games that can be rebuilt to full information (vault ADR-0009) and serve
as the held-out test set. One request per second; resumable (state in the output dir);
main-server replays only (side-server ids like impulse-... are skipped, vault
open-questions). Writes data/train/inputlog/<id>.json.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import httpx

from server.config import ROOT, load_config

MAIN_ID = re.compile(r"^gen9randombattle-\d+$")
SEARCH = "https://replay.pokemonshowdown.com/search.json"
REPLAY = "https://replay.pokemonshowdown.com/{}.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=14)
    ap.add_argument("--format", default="gen9randombattle")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "train" / "inputlog")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--max", type=int, default=0, help="stop after this many new replays (0 = no limit)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    state_file = args.out / "_state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    cutoff = int(time.time() - args.days * 86400)
    before = state.get("before")  # resume point: page older than this upload time
    http = httpx.Client(headers={"User-Agent": load_config().user_agent}, timeout=30, follow_redirects=True)
    saved = skipped = errors = 0
    last = 0.0

    def get(url: str, **params):
        """GET with spacing; network errors, 429 and 5xx are retried with growing waits
        (a single connection reset used to end a multi-hour run)."""
        nonlocal last
        for attempt in range(8):
            wait = last + args.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                r = http.get(url, params=params or None)
            except httpx.TransportError as e:
                r, why = None, f"{type(e).__name__}: {e}"
            else:
                why = f"HTTP {r.status_code}"
            finally:
                last = time.monotonic()
            if r is not None and r.status_code != 429 and r.status_code < 500:
                return r
            pause = min(30 * 2 ** attempt, 900)
            print(f"{time.strftime('%H:%M:%S')} {why}; retrying in {pause} s", flush=True)
            time.sleep(pause)
        raise RuntimeError(f"giving up on {url} after 8 attempts")

    while True:
        params = {"format": args.format}
        if before:
            params["before"] = before
        r = get(SEARCH, **params)
        if r.status_code != 200:
            print(f"search failed: HTTP {r.status_code}; retrying in 60 s", flush=True)
            time.sleep(60)
            continue
        page = r.json()
        if not page:
            break
        for item in page[:50]:
            rid = item["id"]
            if item["uploadtime"] < cutoff:
                print(f"reached the {args.days}-day cutoff", flush=True)
                page = []
                break
            target = args.out / f"{rid}.json"
            if not MAIN_ID.match(rid) or item.get("password") or target.exists():
                skipped += 1
                continue
            rr = get(REPLAY.format(rid))
            if rr.status_code != 200:
                errors += 1
                continue
            data = rr.json()
            if not data.get("inputlog"):
                skipped += 1
                continue
            tmp = target.with_suffix(".part")
            tmp.write_text(json.dumps(data))
            tmp.replace(target)
            saved += 1
            if saved % 100 == 0:
                print(f"{time.strftime('%H:%M:%S')} saved {saved}, skipped {skipped}, errors {errors}; "
                      f"at {time.strftime('%Y-%m-%d %H:%M', time.gmtime(item['uploadtime']))} UTC", flush=True)
            if args.max and saved >= args.max:
                page = []
                break
        if len(page) <= 50:
            break
        before = page[49]["uploadtime"]
        state_file.write_text(json.dumps({"before": before}))
    print(f"done: saved {saved}, skipped {skipped}, errors {errors}", flush=True)


if __name__ == "__main__":
    main()
