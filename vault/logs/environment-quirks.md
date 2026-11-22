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
- PyTorch and other ML packages may not have wheels for 3.14 yet. Make a `uv` venv on an older supported version ([[environment]], [[open-questions]] #8).

## Related
- [[environment]] · [[data-sources]] · [[template-debug-log]]
