---
title: Open questions
type: spec
status: active
tags: [area/vault]
updated: 2026-11-23
---

# Open questions

Items wait here until they are answered. When an item is answered, record the answer in a `raw/` note, update the affected notes, and move the item to **Resolved**. Items marked *(research)* are for Claude to look up, not for the user.

## Open
1. *(test, needs the user)* **First real-browser run of the userscript:** play one game with Tampermonkey on, then check (a) the game appears, (b) whether Chrome showed a Local Network Access prompt, (c) whether the private check works (Tampermonkey log shows `private search:` errors if the login cookie isn't sent to replay.pokemonshowdown.com), (d) after uploading, the poller upgrades the same id, which confirms room ids match replay ids. The `searchprivate` URL is settled: the replay site itself calls `/api/replays/searchprivate?username=` and gets `]` + JSON ([[spec-replay-sync]]).

6. **Codex review, model-testing changes:** items 1–3 done 2026-11-23 ([[ADR-0016-two-view-scoring-strict-gate]]). Still open: adopt items 4–5 in [[plan-run-v12]] (gate fix, two-view scoring, strict pairing, game-balanced value test, careful C/D readout)? Recommendation: 1–3 now (small, checked), 4 as one extra ~50 min test before the overnight run ([[2026-11-23-codex-review]]).
7. *(research)* **Verify the new references** before relying on them: Nessie, Mew's Truck, Ninjask, Eevenator, Mega Evolution rules for Reg M-C ([[2026-11-23-codex-review]]).

8. **What "public" means for the encoder** (Codex finding 2, second part): uploaded randbats logs carry exact HP for both sides, and the encoder leaves out the player's own unseen bench. Decide one mask for training, testing and the move review's leaf. Impact unmeasured ([[2026-11-23-codex-review]]).


12. *(research)* **Profile the move review** (simulator vs network vs Python) before choosing how to speed up depth 2 ([[goals-endgame]]).

13. **Verdict bank labels:** how many choices will the user label blind (the bank also works with search-based references alone) ([[plan-grade-quality]])?



## Resolved
- **Side-server replays** (was #2) → main server only, 2026-11-23 ([[2026-11-23-open-questions-2-to-5]]); `training/collect.py` already skips them.
- **Poll interval** (was #3) → 5 minutes; `SGR_POLL_MINUTES` default changed from 15 to 5, 2026-11-23 ([[2026-11-23-open-questions-2-to-5]]).
- **Frontend UI framework** (was #4) → not relevant anymore (built in plain TypeScript), 2026-11-23 ([[2026-11-23-open-questions-2-to-5]]).
- **Install SpriteCook** (was #5) → yes, 2026-11-23 ([[2026-11-23-open-questions-2-to-5]]). Install is the user's step (plugin card offered); battle visuals still use official sprites only, so SpriteCook is for UI art ([[visual-style]]).
- **Sprites for Gen 6+ Pokémon** (was #14): resolved 2026-11-23. Smogon sprite project sprites count as official ([[2026-11-23-audit-fixes-go-sprite-project-official]]).
- **Which design-audit fixes** (was #15): resolved 2026-11-23. The confirmed bugs and accessibility items first ([[2026-11-23-audit-fixes-go-sprite-project-official]]).
- **Publish the trained model** → yes: release `model-main-9000`, downloaded and checked by `setup.sh` ([[2026-11-23-publish-model]], [[ADR-0021-publish-model]]), 2026-11-23.
- **Change of emphasis** → adopted: after `v12` is read, close model testing; then grade quality, then the UI ([[2026-11-23-adopt-grade-quality-next]], [[ADR-0018-grade-quality-before-ui]]), 2026-11-23.
- **Search weight 0.75 on fresh games** → holds: −0.0063 [−0.0109, −0.0022] on 100 new games; 0.7–0.8 flat ([[2026-11-23-search-blend-fresh-check]]), 2026-11-23.
- **Overnight run** → started 2026-11-23 03:56 EST: `RUN=v12`, games since 2025-01-01, C's settings, 3 epochs, 9 h ceiling ([[2026-11-23-endgame-goals-and-overnight-go]]).
- **Eval bar from search** → yes, built first, before the overnight run ([[2026-11-23-search-bar-first]], [[ADR-0017-eval-bar-search-blend]]), 2026-11-23.
- **Hindsight in move review** → it matters: grading with the real sets changes 21% of verdicts and 6% of flags on 12 games, about 3× sampling noise; worlds mode is now the default ([[ADR-0015-move-review-sampled-worlds]], [[2026-11-22-worlds-vs-perfect-results]]), 2026-11-22.
- **P0 before the overnight run** → yes; built and passed the paired gate vs test2 ([[2026-11-22-p0-ab-results]]), 2026-11-22.
- **ADR-0009** → accepted: train on full-information games rebuilt from inputlogs at their exact commit ([[2026-11-22-adr-0009-decision]]), 2026-11-22.
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
