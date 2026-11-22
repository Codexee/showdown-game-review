---
title: Open questions
type: spec
status: active
tags: [area/vault]
updated: 2026-11-22
---

# Open questions

Items wait here until they are answered. When an item is answered, record the answer in a `raw/` note, update the affected notes, and move the item to **Resolved**. Items marked *(research)* are for Claude to look up, not for the user.

## Open
1. *(test, needs the user)* **First real-browser run of the userscript:** play one game with Tampermonkey on, then check (a) the game appears, (b) whether Chrome showed a Local Network Access prompt, (c) whether the private check works (Tampermonkey log shows `private search:` errors if the login cookie isn't sent to replay.pokemonshowdown.com), (d) after uploading, the poller upgrades the same id, which confirms room ids match replay ids. The `searchprivate` URL is settled: the replay site itself calls `/api/replays/searchprivate?username=` and gets `]` + JSON ([[spec-replay-sync]]).
2. **Accept ADR-0009?** The prototype rebuilt 61/61 replays exactly at their commit ([[2026-11-22-rebuild-prototype-results]]). Recommendation: accept.
3. **Side-server replays** (e.g. `impulse-…`): include them in training data (each adds a checkout) or filter to main-server ids only? Recommendation: main server only.
4. **Poll interval** for the replay poller. Default 15 minutes unless the user says otherwise ([[spec-replay-sync]]).
5. **Frontend UI framework** (Preact, Svelte or none). Decide at the UI stage ([[ADR-0007-app-stack]]).
6. **Install SpriteCook** when the UI stage starts ([[tooling]]).

## Resolved
- **Private replays method** → the userscript lists them with your browser login and sends only ids and passwords; the server fetches `<id>-<pw>pw.json` with no login ([[spec-replay-sync]], [[2026-11-22-research-round-2]]), 2026-11-22.
- **Userscript hook** → wrap `app.receive` / `PS.receive`, finish on `|win|` / `|tie`, send through Tampermonkey `GM_xmlhttpRequest` ([[spec-replay-sync]]), 2026-11-22.
- **Python version** → 3.13 in a uv venv ([[ADR-0008-python-313]]), 2026-11-22.
- **Randbats set data** → `sets.json` + `teams.ts` in Showdown; probabilities from `data.pkmn.cc/randbats/stats/` ([[data-sources]]), 2026-11-22.
- **Format target** → Gen 9 randbats, then VGC Reg M-C ([[ADR-0002-format-order]]), 2026-11-22.
- **Which randbats** → standard [Gen 9] Random Battle, `gen9randombattle` ([[2026-11-22-interview-round-2]]), 2026-11-22.
- **Training time** → overnight 8–12 h ([[ADR-0005-overnight-training-budget]]), 2026-11-22.
- **Where the app runs** → local web app, pixel-art style ([[ADR-0001-local-web-app]], [[ADR-0004-pixel-art-style]]), 2026-11-22.
- **Stack** → FastAPI + Vite/TypeScript + SQLite ([[ADR-0007-app-stack]]), 2026-11-22.
- **Username** → `Codexe` ([[2026-11-22-interview-round-2]]), 2026-11-22.
- **Which games to save** → every finished game from now on, no backfill; poller first, then userscript ([[ADR-0006-replay-archive]]), 2026-11-22.
- **Private replays** → include them ([[2026-11-22-interview-round-2]]); the method is still open (#1), 2026-11-22.
- **Formats to save and list** → all formats; eval only where a model exists ([[spec-replay-sync]]), 2026-11-22.
- **Ways to load a game** → username sync, paste a replay URL, upload a log/HTML file, add your own team paste ([[spec-replay-sync]]), 2026-11-22.
- **1.5% usage rule** → keep it for VGC Reg M-C; it does not apply to randbats, whose set pool is fixed ([[spec-eval-model]]), 2026-11-22.

## Related
- [[index]] · [[2026-11-22-interview-round-1]] · [[2026-11-22-interview-round-2]]
