---
title: Research round 2 (randbats data, Python, private replays, userscript)
type: raw
date: 2026-11-22
source: GitHub API, PyPI JSON API, live Showdown endpoints and two web searches, run in session 15119347
---

# Research round 2 (raw)

Do not edit. Synthesized into [[data-sources]], [[environment]], [[spec-replay-sync]], [[spec-eval-model]], [[ADR-0008-python-313]], [[ADR-0009-randbats-full-info-reconstruction]] and [[open-questions]].

## 1. Gen 9 Random Battle set data
- `smogon/pokemon-showdown` `data/random-battles/gen9/`: `sets.json` (267,488 bytes), `doubles-sets.json`, `factory-sets.json`, `bss-factory-sets.json`, `1v1-factory-sets.json`, `draft-factory-matchups.json`, `teams.ts`.
- `sets.json`: 509 species. Per species: `level` and `sets[]`. Each set has `role`, `movepool`, `abilities`, `teraTypes`. **No items, EVs or IVs.**
- Roles: Bulky Setup, AV Pivot, Tera Blast user, Fast Attacker, Setup Sweeper, Bulky Attacker, Fast Bulky Setup, Fast Support, Bulky Support, Wallbreaker.
- `teams.ts` picks items and abilities in code (`getItem` line 1347, `getPriorityItem` 1157, `getAbility` 1109, `cullMovePool` 463, `randomSet` 1498, `randomTeam` 1752). Default EVs 85 in each stat, IVs 31; HP EVs are lowered in a loop for some species (line 1568).
- **pkmn/randbats** (pushed 2026-11-20): `https://data.pkmn.cc/randbats/gen9randombattle.json` (509 species, possible items/abilities/tera/moves per role) and `https://data.pkmn.cc/randbats/stats/gen9randombattle.json` (**probabilities**: role weight, and per role the frequency of each ability, item, tera type, move, plus EVs). Example: Abomasnow Bulky Support: Earthquake 0.6828, Ice Shard 0.6636, Wood Hammer 0.6536, Tera Ghost 0.5211 / Water 0.4789, EVs hp 77.

## 2. Python versions (PyPI, 2026-11-22)
- torch 2.15.0 (2026-10-28): requires Python ≥3.11; macOS arm64 wheels for cp311–cp315.
- poke-env 0.17.0 (2026-11-15): requires ≥3.10; pure-Python wheel.
- poke-engine 0.0.48 (2026-07-19): **source only, no wheels**. Built with maturin; `pyo3 = 0.29.0`. Cargo features include `gen9` and `terastallization`.
- foul-play `requirements.txt`: `poke-engine==0.0.48 --config-settings="build-args=--features poke-engine/terastallization --no-default-features"`. foul-play's Dockerfile builds on `rust:1.89-slim` with **python3.13** and runs on `python:3.13-slim`.
- fastapi 0.165.0 (2026-11-18): requires ≥3.11.
- This Mac: rustc 1.99.1, cargo 1.99.1 installed. uv sees cpython 3.14.10 (Homebrew), 3.14.6 (Anaconda), 3.12.16 (uv-managed), 3.9.6 (system); 3.13.18 available to download.

## 3. Private replays (smogon/pokemon-showdown-loginserver, `src/replays.ts`, `src/actions.ts`)
- `replays/searchprivate`: requires a logged-in user (`getUser()`; session `sid` cookie, or `sid` in the body), and the user must be one of the searched usernames (or a sysop). Calls `verifyCrossDomainRequest()` (CORS only for origins in `Config.cors`).
- It passes `page` but **not** `before` to the search (the `before` parameter is parsed then unused). Pages are 51 results, offset 50, max page 100.
- Search results include `password`. A private replay's full id is `<id>-<password>pw`. `replays/get.json`, `get.log` and `get.inputlog` return 404 unless the password suffix matches. With the suffix, no login is needed.
- Private flag values: 0 public, 1 private with password, 2 private without password (legacy).
- On `replay.pokemonshowdown.com`, `.htaccess` rewrites `/api/*` to the login server, `search.json` to `/api/replays/search.json`, and `<id>.json|.log|.inputlog` to `/api/replays/get.*`.

## 4. Inputlogs
- `Replays.isSafeInputlog`: true for formats ending in `randombattle`, `randomdoublesbattle`, `challengecup`, `challengecup1v1`, `battlefactory`, `bssfactory`, `hackmonscup`. For those, `get.json` includes `inputlog`.
- Live check: newest `gen9randombattle` replay (`gen9randombattle-2717787993`) JSON keys: format, formatid, id, inputlog, log, password, players, private, rating, uploadtime, views. Its inputlog (48 lines) starts:
  ```
  >version ac7b7da0f9d7ae79a5b021be49de854f01534bb5
  >start {"formatid":"gen9randombattle","seed":"sodium,…","rated":"Rated battle"}
  >player p1 {"name":"…","avatar":"…","rating":1808,"seed":"sodium,…"}
  >player p2 {"name":"…","avatar":"…","rating":1812,"seed":"sodium,…"}
  >p1 move toxicspikes
  >p2 switch 3
  ```
- `ac7b7da0f9` is a real smogon/pokemon-showdown commit (2026-11-13, "Ladder: Cache bot matchmaking prefs on search").
- `WEB-API.md` (pokemon-showdown-client): APIs send `Access-Control-Allow-Origin: *`; search is 51 results with 50 offset; paginate with `before=<uploadtime of last result>`; `page=` is "poorly supported". It asks people not to scrape the replay HTML pages.

## 5. Userscript hook
- play.pokemonshowdown.com currently loads the **old client**: `js/oldclient/client.js` (Backbone `app`), plus SockJS. A new client exists in the repo (`index-new.html`, `src/client-main.ts`).
- Old client: socket `onmessage` → `self.receive(msg.data)` (line 858–862); `app.receive: function (data)` (line 1006) routes `>roomid\n…` blocks to `this.rooms[roomid].receive(data)` (line 1103).
- New client: `src/client-connection.ts` may run the socket **in a Web Worker** (`new Worker('/js/client-connection-worker.js')`) and calls `PS.receive(data)` (lines 101 and 156).
- Chrome **Local Network Access**: from Chrome 142 (announced 2025), a public page's `fetch()` to `localhost`/`127.0.0.1` shows a permission prompt; Chrome advises triggering such requests from a user gesture. Source: https://developer.chrome.com/blog/local-network-access and https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access
- **Tampermonkey**: `// @grant GM_xmlhttpRequest` plus `// @connect localhost` lets a script call localhost through the extension, outside the page's CORS rules. Source: https://www.tampermonkey.net/documentation.php?q=connect
