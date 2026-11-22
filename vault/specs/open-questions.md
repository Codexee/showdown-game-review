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
1. *(research)* **Private replays:** how to list and fetch a user's private replays without the app storing the password. Fallback: the userscript captures private games going forward ([[ADR-0006-replay-archive]]).
2. *(research)* **Userscript hook:** which Showdown client event marks a finished battle, and whether the browser allows a request from play.pokemonshowdown.com to localhost ([[spec-replay-sync]]).
3. *(research)* **Python version** that PyTorch, poke-env and poke-engine all support on this Mac ([[environment]]).
4. *(research)* **Gen 9 Random Battle set data:** where Showdown keeps the random-set pools (file path and format) so the model can use them as priors ([[spec-eval-model]]).
5. **Poll interval** for the replay poller. Default 15 minutes unless the user says otherwise ([[spec-replay-sync]]).
6. **Frontend UI framework** (Preact, Svelte or none). Decide at the UI stage ([[ADR-0007-app-stack]]).
7. **Install SpriteCook** when the UI stage starts ([[tooling]]).

## Resolved
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
