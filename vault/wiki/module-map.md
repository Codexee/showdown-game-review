---
title: Module map (code)
type: wiki
status: active
tags: [area/data, area/ui, area/infra]
updated: 2026-11-22
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

Environment variables (`server/config.py`): `SR_DATA_DIR` (default `./data`), `SR_USERNAME` (default `Codexe`; the app's saved setting wins), `SR_POLL_MINUTES` (15), `SR_REQUEST_DELAY` (1.0 s between Showdown requests), `SR_POLLER=0` turns the background poller off.

## Backend: `server/` (Python 3.13, FastAPI; [[ADR-0007-app-stack]], [[ADR-0008-python-313]])
| File | Job |
|---|---|
| `config.py` | Paths and defaults from env vars. |
| `ids.py` | `to_id` (Showdown's toID), `parse_replay_ref` (URL / id / `-<pw>pw` suffix → id + password). |
| `logsummary.py` | Reads the game-list details out of a battle log: players, ratings before/after (from `\|raw\|` lines), winner, turns, teams (`\|poke\|` with team preview, otherwise switch-ins keyed by nickname), start/end time. Not the per-turn parser (stage 3). |
| `archive.py` | SQLite index (`games`, `settings`) plus raw files under `data/replays/<format>/<id>.{json,log,inputlog}`. Never deletes. Re-saving a stored game changes nothing, except a later copy with an inputlog adds it. [[ADR-0006-replay-archive]] |
| `showdown.py` | Async client for `users/<id>.json`, `search.json`, `<id>.json`. Generic user agent, 1 s spacing ([[environment-quirks]]). |
| `sync.py` | Poller logic. The first sync records a start time; only replays uploaded after it are saved (no backfill). Pages with `before=`. Stops at a per-user high-water mark (`poll_cursor:<user>`), **not** at the first known game, because the userscript can store a newer game first. Fetches a known game again only if `archive.needs()` (userscript copy, or a random format missing its inputlog). |
| `ingest.py` | Stage 2b. `/api/ingest`: room id → game id, drops client-only lines (`\|init\|`, `\|request\|`, …), stores with `source=userscript`, keeps your `\|request\|` side data as `own_team`. `/api/ingest-private`: downloads `<id>-<pw>pw.json` for each listed private replay newer than the start time. |
| `imports.py` | Uploaded `.log`, replay `.json`, or saved replay `.html` → replay record. Uploads without a replay id get `upload-<sha1>`. |
| `app.py` | FastAPI routes (below), origin guard middleware ([[ADR-0010-local-api-origin-guard]]), background poller task, serves `web/dist` and the userscript. |

`archive.py` also validates every game id and format id before using them as file names (an uploaded `.json` could otherwise write outside `data/`).

### API
`GET/PUT /api/settings` · `GET /api/profile[?refresh=true]` · `POST /api/sync` · `GET /api/sync` · `GET /api/formats` · `GET /api/games?format=&result=&opponent=` · `GET /api/games/{id}` · `PUT /api/games/{id}/team` · `POST /api/import/url` · `POST /api/import/file` · `POST /api/ingest` · `POST /api/ingest-private` · `GET /userscript/showdown-review.user.js`

## Userscript: `userscript/`
| File | Job |
|---|---|
| `showdown-review.user.js` | Tampermonkey script for play.pokemonshowdown.com. Wraps `app.receive` (old client) or `PS.receive` (new client); buffers each battle room from `\|init\|battle`; sends 4 s after `\|win\|`/`\|tie` (so rating lines are included), or as `incomplete` on `\|deinit` before the end. Every 15 min it lists private replays with your browser login and sends ids + passwords only. Queues sends in `GM_setValue` when the app is down. |
| `userscript.test.mjs` | 7 Node tests running the script in a `vm` sandbox with a fake client: `node --test userscript/*.test.mjs`. |

## Frontend: `web/` (Vite + TypeScript, no framework yet)
| File | Job |
|---|---|
| `src/api.ts` | Typed fetch wrappers for the API. |
| `src/main.ts` | Game list page: username + sync, ratings, add by URL/file, filters, game list, detail panel with team paste and raw log. Builds DOM with `textContent` only, because player names come from other people. Refreshes every 60 s. |
| `src/style.css` | Plain working styles with light/dark tokens. Replaced by the pixel-art design in stage 4 ([[visual-style]]). |

## Tests: `server/tests/`
- `fixtures/`: two real replays by Codexe (a `gen9randombattle` game with an inputlog, and a `gen9championsvgc2026regmc` game).
- `conftest.py`: `FakeShowdown`, an `httpx.MockTransport` that serves users, search (with `before`) and replays (with password suffixes).
- 27 tests: log summaries, id parsing, no-backfill first sync, add-once, paging, private replays, URL and file import, filters, team paste, settings; ingest, userscript-copy upgrade, the poller regression, private ingest, origin guard, path traversal.

## Not built yet
Per-turn parser (stage 3), review screen (stage 4), model (stage 5). See [[roadmap]].

## Related
- [[architecture]] · [[spec-replay-sync]] · [[roadmap]]
