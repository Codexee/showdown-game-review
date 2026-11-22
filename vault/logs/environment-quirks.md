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

## 2026-11-22: Long runs stall when the lid is closed on battery
- The inputlog crawl crashed at 16,700 replays with `httpx.ReadError: [Errno 54] Connection reset by peer`. *Corrected the same day:* this note first blamed the replay server. The real cause is that the Mac was in clamshell sleep on battery (`pmset -g log`: `Entering Sleep state due to 'Clamshell Sleep' … Using Batt`). It wakes for about 2 s every 16 min ("DarkWake"), so a run saves a few items per wake, and the connection it had open is gone after each sleep, which gives the reset. The server answers in about 0.3 s when the Mac is awake.
- Claude's keep-awake assertion (`PreventUserIdleSystemSleep`) stops idle sleep only. Closing the lid on battery still sleeps. Long runs (crawls, [[ADR-0005-overnight-training-budget]] training) need the lid open, or power plus an external display.
- `training/collect.py` now retries network errors, 429 and 5xx up to 8 times (30 s doubling, 15 min at most) and resumes from `_state.json`, so a sleep no longer ends the run.

## Related
- [[environment]] · [[data-sources]] · [[template-debug-log]]
