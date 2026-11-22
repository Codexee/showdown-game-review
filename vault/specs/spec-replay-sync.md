---
title: Spec: replay sync and game list
type: spec
status: draft
tags: [area/data, area/ui]
updated: 2026-11-22
---

# Spec: replay sync and game list (draft)

> [!note] Status 2026-11-22
> **Built (stage 2a):** profile, poller (public and password-suffixed private replays it can see), archive, game list with filters, URL import, file import (.log/.json/.html), team paste, settings. Code map: [[module-map]]. Checked live: first sync set the start time; two of Codexe's older replays were added by URL.
> **Not built (stage 2b):** userscript, `/api/ingest`, `/api/ingest-private`. Team icons are text names for now; sprites come in stage 4.

Source requests: [[2026-11-22-interview-round-1]] and [[2026-11-22-interview-round-2]]. Storage and capture decisions: [[ADR-0006-replay-archive]].

## User story
The app knows my Showdown username (`Codexe`). It shows my ratings and a list of my games, newest first. Every game I finish from now on is saved on my Mac, in every format, public or private, uploaded or not. I can also open any other game by URL or file.

## Settings
- Username: `Codexe` (the user can change it in the app's settings). More than one username should be possible later.
- Sync start date: the first time sync runs. Nothing older is fetched.

## Functions
1. **Profile.** Fetch `users/<userid>.json`: rating, GXE and games per format ([[data-sources]]). Refresh when the app opens.
2. **Poller (stage 1).** Page through `search.json?user=codexe` until a replay is already in the archive or is older than the start date. Download `.json` and `.log` for each new one. Run when the app opens and every N minutes while the server runs (N **unknown**; 15 is a guess).
   - Paginate with `before=<last uploadtime>` ([[data-sources]]). Store the `inputlog` too when present (random formats).
   - **Private replays:** included. Listing them needs a login (`/api/replays/searchprivate`), but fetching one needs only its password suffix: `<id>-<password>pw.json` ([[2026-11-22-research-round-2]]). So the **userscript**, which already runs in your logged-in browser, calls `searchprivate` for `codexe` and sends only the list of ids and passwords to `/api/ingest-private`. The local server then fetches each `<fullid>.json` with no login. The app never sees your password or session cookie ([[ADR-0006-replay-archive]]).
     - (unverified) The exact URL the userscript should call (`replay.pokemonshowdown.com/api/replays/searchprivate` or the play site's action endpoint) and whether the `sid` cookie is sent. Test once in the browser.
     - `searchprivate` ignores `before`, so page with `page=1,2,…` and stop at a replay already in the archive.
3. **Userscript (stage 2).** A Tampermonkey script on `play.pokemonshowdown.com` ([[2026-11-22-research-round-2]]):
   - **Hook:** wrap `window.app.receive` (old client, live today) or `window.PS.receive` (new client), whichever exists, and pass every message through unchanged. Don't wrap the WebSocket: the new client may run its socket in a Web Worker.
   - **Collect:** for each message block starting `>battle-…`, add its lines to that room's buffer, starting at `|init|battle`.
   - **Battle end:** on a `|win|` or `|tie` line, send `{roomid, format, players, log, ended_at}` to `POST http://localhost:<port>/api/ingest`, then clear the buffer. Also send a partial log if the room closes before the end (forfeit or disconnect), marked `incomplete`.
   - **Your own team:** your `|request|` messages hold your full team. Send the last one too, so your sets are known even for games you never upload.
   - **Transport:** `GM_xmlhttpRequest` with `// @grant GM_xmlhttpRequest` and `// @connect localhost`, so the page's CORS rules and Chrome's Local Network Access prompt for page `fetch()` calls don't apply. (unverified that LNA skips extension requests; test once.) Fallback: plain `fetch()` after a one-time LNA prompt, with FastAPI allowing the `https://play.pokemonshowdown.com` origin on the ingest routes only.
   - **Dedup:** the room id `battle-<format>-<n>` matches the replay id `<format>-<n>`. (unverified; check with one game.) A later upload of the same game upgrades the stored copy with the inputlog.
   - **Retry:** if the local server is down, keep unsent logs in the script's storage (`GM_setValue`) and resend on the next page load.
4. **Archive.** Raw files under `data/replays/<format>/<id>.{json,log}` plus one SQLite row each. Every format. Never delete. Re-running sync or re-sending a game must not create duplicates.
5. **Game list (UI)** shows per game: date, format, opponent, result, rating before/after if the log has it, turn count, both teams as sprite icons, public/private/not-uploaded, and an "analyzed" badge once a model has scored it. Filter by format, result and opponent. Eval bars only for formats that have a model.
6. **Manual input** (all chosen in round 2):
   - Paste a replay URL (anyone's public game).
   - Upload a saved `.log` or replay `.html` file.
   - Add my own team paste (Showdown export format) to a game, so the model uses my exact sets for my side.

## Details to get right
- Send a generic browser-like user agent and wait between requests ([[environment-quirks]]).
- The parser in [[spec-eval-model]] reads from the archive, not from the network.
- Mark which side is the user (`Codexe`) in each game.

## Done when
- Starting sync stores each new game once; a second sync adds nothing.
- A game finished in the browser with the userscript installed appears in the list within a minute, even if it was not uploaded.
- A pasted URL and an uploaded log both open in the review screen.

## Related
- [[data-sources]] · [[spec-review-app]] · [[architecture]] · [[ADR-0007-app-stack]]
