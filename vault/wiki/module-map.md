---
title: Module map (code)
type: wiki
status: active
tags: [area/data, area/ui, area/infra]
updated: 2026-11-23
---

# Module map

What each code file does. Update it when files are added, moved or change role. Design: [[architecture]].

## Run it
```bash
uv run uvicorn server.app:app --host 127.0.0.1 --port 8765   # app at http://127.0.0.1:8765
uv run pytest -q                                              # backend tests
cd web && npm run build                                       # rebuild the page FastAPI serves
cd web && npm run dev                                         # dev server on :5173, proxies /api to :8765
```
The Claude desktop preview config is `.claude/launch.json` (`review-server`).

Setup: `./start.sh` (first run calls `./setup.sh`), see `README.md` ([[ADR-0020-distribution]]). Environment variables (`server/config.py`): `SGR_DATA_DIR` (default `./data`), `SGR_USERNAME` (default empty; the app's saved setting wins), `SGR_POLL_MINUTES` (5; was 15 until 2026-11-23, [[2026-11-23-open-questions-2-to-5]]), `SGR_REQUEST_DELAY` (1.0 s between Showdown requests), `SGR_POLLER=0` turns the background poller off.

## Backend: `server/` (Python 3.13, FastAPI; [[ADR-0007-app-stack]], [[ADR-0008-python-313]])
| File | Job |
|---|---|
| `config.py` | Paths and defaults from env vars. |
| `ids.py` | `to_id` (Showdown's toID), `parse_replay_ref` (URL / id / `-<pw>pw` suffix → id + password). |
| `logsummary.py` | Reads the game-list details out of a battle log: players, ratings before/after (from `\|raw\|` lines), winner, turns, teams (`\|poke\|` with team preview, otherwise switch-ins keyed by nickname), start/end time. Not the per-turn parser (stage 3). |
| `archive.py` | SQLite index (`games`, `settings`) plus raw files under `data/replays/<format>/<id>.{json,log,inputlog}`. Never deletes. Re-saving a stored game changes nothing, except a later copy with an inputlog adds it. [[ADR-0006-replay-archive]] |
| `showdown.py` | Async client for `users/<id>.json`, `search.json`, `<id>.json`. Generic user agent, 1 s spacing ([[environment-quirks]]). |
| `sync.py` | Poller logic. The first sync records a start time; only replays uploaded after it are saved (no backfill). Pages with `before=`. Stops at a per-user high-water mark (`poll_cursor:<user>`), **not** at the first known game, because the userscript can store a newer game first. Fetches a known game again only if `archive.needs()` (a userscript copy with no upload time yet, or a random format missing its inputlog; an upgraded copy no longer counts, fixed 2026-11-23). |
| `ingest.py` | Stage 2b. `/api/ingest`: room id → game id, drops client-only lines (`\|init\|`, `\|request\|`, …), stores with `source=userscript`, keeps your `\|request\|` side data as `own_team`. `/api/ingest-private`: downloads `<id>-<pw>pw.json` for each listed private replay newer than the start time. `/api/ingest-uploaded` (2026-11-23, [[ADR-0022-auto-upload-replays]]): one replay-server fetch for a room the userscript just uploaded (password from a `-<pw>pw` room id). Returns `found`. A hit upgrades the copy, so auto-analysis runs. |
| `imports.py` | Uploaded `.log`, replay `.json`, or saved replay `.html` → replay record. Uploads without a replay id get `upload-<sha1>`. |
| `battle/` | Stage 3 log parser ([[battle-parser]]). `state.py` dataclasses; `parser.py` protocol → state at each `\|turn\|` + final; `view.py` per-player view (opponent HP as Showdown displays it); `data/forme_abilities.json` (126 in-battle formes → their fixed ability, generated from Showdown's pokedex at ac7b7da0f9). |
| `battle/narrate.py` | Readable event lines per turn ("Metagross was paralyzed (Static).") for the review screen. |
| `evaluate.py` | **Placeholder** win chance per state: logistic on the remaining-HP lead (0.5 per Pokémon of HP; unseen opponents count as full). Replaced by the model in stage 5. |
| `sprites.py` | `sprite_id(species)` (Showdown's naming: `palafin-hero`, `hooh`, `kommoo-totem`) and a disk cache for `/sprites/gen5[-back]/<id>.png` (remembers 404s too). |
| `review/` | Stage 6 move review ([[ADR-0014-move-review-method]]). `engine.py` drives `tools/review-engine.cjs` (one Node process per game, built at the inputlog's commit via `training.rebuild.checkout`). `analyze.py` prunes choices with the policy head, expands pairs, scores leaves with the value head, solves the matrix (regret matching+), and returns per-turn verdicts, luck and a per-player summary. `worlds.py` samples the opponent's hidden set parts from the randbats data for worlds mode ([[ADR-0015-move-review-sampled-worlds]]). `jobs.py` runs one job at a time in a thread and caches results in `data/analysis/<id>.json`, tagged with the model. |
| `app.py` | FastAPI routes (below), origin guard middleware ([[ADR-0010-local-api-origin-guard]]), background poller task, serves `web/dist` and the userscript. |

`archive.py` also validates every game id and format id before using them as file names (an uploaded `.json` could otherwise write outside `data/`).

### API
`GET/PUT /api/settings` (incl. `auto_analyze`) · `GET /api/profile[?refresh=true]` · `POST /api/sync` · `GET /api/sync` · `GET /api/formats` · `GET /api/games?format=&result=&opponent=` · `GET /api/games/{id}` · `GET /api/games/{id}/turns?side=p1|p2|all` · `GET /api/games/{id}/review?side=p1|p2` · `GET/POST /api/games/{id}/analysis` (body: `seeds`, `top_k`, `mode` worlds|perfect) · `GET /sprites/{gen5|gen5-back|gen5ani|gen5ani-back|sub|sub-back|item|gen5mini}/{id}.png` (+ `.json` frame data for gen5ani) · `PUT /api/games/{id}/team` · `POST /api/import/url` · `POST /api/import/file` · `POST /api/ingest` · `POST /api/ingest-private` · `POST /api/ingest-uploaded` · `GET /userscript/showdown-game-review.user.js`

## Userscript: `userscript/`
| File | Job |
|---|---|
| `showdown-game-review.user.js` | Tampermonkey script for play.pokemonshowdown.com. Wraps `app.receive` (old client) or `PS.receive` (new client); buffers each battle room from `\|init\|battle`; sends 4 s after `\|win\|`/`\|tie` (so rating lines are included), or as `incomplete` on `\|deinit` before the end. Every 15 min it lists private replays with your browser login and sends ids + passwords only. Queues sends in `GM_setValue` when the app is down. **Auto-upload** (v0.3.0, [[ADR-0022-auto-upload-replays]], private per [[ADR-0023-auto-upload-private]]): sends `/hidereplay` once at `\|start\|` of a game you play (skipped if the log already shows the notice); after the end sends `/savereplay silent` to the room (room `send`, else client `send(text, roomid)`). Follows `\|noinit\|rename\|` for hidden battles. Calls `/api/ingest-uploaded` at 8/30/120 s, then lists private replays once. Switch in the Tampermonkey menu (`autoUpload`, default on). |
| `userscript.test.mjs` | 19 Node tests (12 for auto-upload: both clients, send fallback, retries, private fallback, rename, spectator, switch off, unfinished, app down, hide once after reload, hide when joined after the end) running the script in a `vm` sandbox with a fake client: `node --test userscript/*.test.mjs`. |

## Frontend: `web/` (Vite + TypeScript, no framework)
| File | Job |
|---|---|
| `src/main.ts` | Hash router (`#/`, `#/game/<id>/<step>`), fonts, global key handler. |
| `src/api.ts` | Typed fetch wrappers and types for the API (incl. `Review`, `Step`, `Mon`). |
| `src/dom.ts` | `h()` / `s()` element builders (text via `textContent` only: names come from other people), formatters, status line, `sprite()`. |
| `src/list.ts` | Games page: trainer card, add a game, userscript help, filtered game list with mini team sprites. Refreshes every 60 s. |
| `src/review.ts` | Review screen ([[spec-review-app]]): DS top screen, eval bar, hinge, graph, turn list, events, view-as-opponent, team paste; move review bar, verdict marks, per-turn review box (polls the job every 2 s). |
| `src/style.css` | Design tokens and all styles ([[visual-style]]). |

Fonts come from `@fontsource/dotgothic16` and `@fontsource/atkinson-hyperlegible`.

## Tests: `server/tests/`
- `fixtures/`: two real replays by Codexe (a `gen9randombattle` game with an inputlog, and a `gen9championsvgc2026regmc` game).
- `conftest.py`: `FakeShowdown`, an `httpx.MockTransport` that serves users, search (with `before`) and replays (with password suffixes).
- 27 tests: log summaries, id parsing, no-backfill first sync, add-once, paging, private replays, URL and file import, filters, team paste, settings; ingest, userscript-copy upgrade, the poller regression, private ingest, origin guard, path traversal.

## Tools: `tools/`
| File | Job |
|---|---|
| `sim-states.cjs` | `node tools/sim-states.cjs <built-showdown-dir> <replay.json>...`: replays inputlogs and prints the true state at each turn start (ground truth; also the full-information training target, [[ADR-0009-randbats-full-info-reconstruction]]). |
| `review-engine.cjs` | `node tools/review-engine.cjs <built-showdown-dir>`: JSON-lines service. `load` replays an inputlog and keeps each turn-start snapshot (as a JSON string), the legal choices and the played choice; `expand` runs choice pairs from a snapshot with seeded PRNGs and branches over forced replacements; `options` and `expand_jobs` do the same inside a sampled world (overridden moves, item, ability, Tera type). |
| `compare_parser.py` | `uv run python -m tools.compare_parser <replays-dir> <truth.jsonl>`: grades the parser field by field and separates "not knowable from the log" ([[2026-11-22-parser-accuracy-results]]). |

## Training: `training/` (stage 5, [[spec-eval-model]])
| File | Job |
|---|---|
| `download_hf.sh` | Downloads the HF Gen 9 randbats parquet files to `data/hf/` (resumable). |
| `collect.py` | `python -m training.collect --days 14`: recent replays with inputlogs from Showdown's API, 1 req/s, resumable, main server only → `data/train/inputlog/`. |
| `rebuild.py` | `python -m training.rebuild`: per-commit Showdown checkouts (`data/sim/`), runs `tools/sim-states.cjs`, writes truth + log-match check to `data/train/truth/<sha10>.jsonl.gz`. |
| `vocab.json` | Fixed vocabulary from Showdown's data at ac7b7da0f9. |
| `features.py` | `encode(state, side)` → 13 tokens; `turn_actions(log)`; `game_samples(log)`. |
| `build_dataset.py` | `python -m training.build_dataset --name … --hf … --since …` (or `--inputlog`): multiprocess → memory-mapped arrays in `data/train/ds/<name>/`. |
| `tables.py` | Fixed lookup tables built from `dex.json` (Showdown dex: base stats, types, move properties) and `randbats_gen9.json` (pkmn/randbats priors, MIT). |
| `model.py` | `EvalNet` v1.1: tokens with property tables and randbats-prior mixes; value, policy, opponent's-choice and hidden-set heads; switch mask per side. |
| `metrics.py` | Temperature fit, ECE, by-phase scores, bootstrap CIs over games, 1500+ slice, paired comparison, `two_view` (both players' views averaged; needs `--both-sides` rows). |
| `compare_runs.py` | Paired gate: two runs' predictions on the same pinned samples (`preds_<data>.npz`), Δ log-loss / Brier with 90% bands. Stops unless both files have the same keys and labels. `--view two` (default) or `single`. |
| `train.py` | `python -m training.train --data … --run … --hours …`: MPS training, checkpoints, resume, metrics vs placeholder. |
| `test_model.py` | Scores a run on another dataset (the pinned bank `test_pinned`) with the validation temperature; writes the report (with a `two_view` section) and per-sample predictions. |
| `export.py` | Installs a run as `data/models/current.pt` for the app. |
| `overnight.sh` | Build or check the dataset → train (9 h ceiling) → test → gate → install only if better, with `caffeinate`. `RUN=<new name>`; variables `SINCE`/`RANGES`, `EPOCHS`, `DROPOUT`, `WD`, `VW_FLOOR`; `RESUME=1`, `DRY_RUN=1`, `INSTALL_IF_TIE=1`. Log: `data/models/<run>.log`. |

`web/src/gallery.ts`: `#/gallery`, every battle-screen element as example turns on the real review screen.

`server/model_eval.py` loads `data/models/current.pt` (reloads when it changes) for the review endpoint; it averages both players' views ([[ADR-0016-two-view-scoring-strict-gate]]); after a current worlds-mode move review, the review endpoint blends in its search, 75/25 ([[ADR-0017-eval-bar-search-blend]]); doubles keep the placeholder.

`tests_v12.sh` runs the four v1.2 tests and gates ([[plan-run-v12]]). `train.py` also takes `--dropout` and `--value-weight-floor`; `build_dataset.py` takes `--ranges` for several date ranges.

## Prototypes: `prototypes/`
| Folder | Job |
|---|---|
| `inputlog-rebuild/` | `rebuild.cjs` runs a built Showdown checkout on replay inputlogs and checks the rebuilt log against the replay ([[ADR-0009-randbats-full-info-reconstruction]]). Data and checkouts live in `data/proto/` (git-ignored). |

- `test_battle_parser.py`: 17 real replays in `fixtures/battles/` covering the tricky mechanics, graded against simulator truth (`fixtures/battles/truth.jsonl`), plus unit tests. Also grades all 261 local games in `data/proto` when present (skipped otherwise). 56 tests in total.

- `test_review.py`: sprite ids and proxy cache, narration, placeholder eval, review endpoint. 68 Python tests in total.

- `test_training.py`: actions, encoding, switch mask, model shapes, review endpoint using an installed model (singles only). 73 Python tests in total.

- `test_move_review.py`: accuracy curve, verdict bands, the matrix solver, labels, summary, job gating, analysis API validation, and the engine against the real sim build (skipped without it); world sampling (revealed facts kept, 4 moves, seeded, opponent only) and world overrides in the engine. 95 Python tests in total.

## Not built yet
Sampling unseen opposing species in move review, VGC (stage 7). See [[roadmap]].

## Related
- [[architecture]] · [[spec-replay-sync]] · [[roadmap]]
