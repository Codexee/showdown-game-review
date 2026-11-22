---
title: Environment quirks
type: log
tags: [area/infra, area/data]
updated: 2026-11-22
---

# Environment quirks

Short entries. Newest first.

## 2026-11-22: Showdown replay API returns 403 to Python's default user agent
- **Symptom:** `urllib.request.urlopen("https://replay.pokemonshowdown.com/search.json?...")` raised `HTTPError 403: Forbidden`. The same URL worked with `curl` ([[2026-11-22-research-findings]]).
- **Cause:** the server blocks the default `Python-urllib/3.x` user agent. (Inferred from the curl result, not confirmed by Showdown docs.)
- **Fix:** send an explicit `User-Agent` header with a generic client name (not personal details). Keep a delay between requests.

## 2026-11-22: System Python is 3.14 from Anaconda
- Don't use it for the project. Use the uv venv on 3.13 ([[ADR-0008-python-313]]). PyTorch does ship 3.14 wheels, but foul-play's poke-engine build is tested on 3.13.

## 2026-11-22: poke-engine has no wheels
- `pip install poke-engine` compiles Rust. Pass the Gen 9 feature flags, or it builds for the default generation ([[ADR-0008-python-313]]).

## 2026-11-22: `searchprivate` ignores `before`
- The private replay search parses `before` but never passes it on. Page with `page=` instead ([[2026-11-22-research-round-2]]).

## 2026-11-22: Long replay crawls get connection resets
- After about 16,700 replays at 1 request/s, `replay.pokemonshowdown.com` reset a connection (`httpx.ReadError: [Errno 54] Connection reset by peer`). Just before that, throughput fell from about 2 minutes to about 20 minutes per 100 replays (`data/train/collect.log`).
- `training/collect.py` had no retry, so the run ended. It now retries network errors, 429 and 5xx up to 8 times, waiting 30 s and doubling each time (15 min at most), and resumes from `_state.json`.

## Related
- [[environment]] · [[data-sources]] · [[template-debug-log]]
