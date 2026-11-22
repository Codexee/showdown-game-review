---
title: Spec: replay sync and game list
type: spec
status: draft
tags: [area/data, area/ui]
updated: 2026-11-22
---

# Spec: replay sync and game list (draft)

Source requests: [[2026-11-22-interview-round-1]] and [[2026-11-22-interview-round-2]]. Storage and capture decisions: [[ADR-0006-replay-archive]].

## User story
The app knows my Showdown username (`Codexe`). It shows my ratings and a list of my games, newest first. Every game I finish from now on is saved on my Mac, in every format, public or private, uploaded or not. I can also open any other game by URL or file.

## Settings
- Username: `Codexe` (the user can change it in the app's settings). More than one username should be possible later.
- Sync start date: the first time sync runs. Nothing older is fetched.

## Functions
1. **Profile.** Fetch `users/<userid>.json`: rating, GXE and games per format ([[data-sources]]). Refresh when the app opens.
2. **Poller (stage 1).** Page through `search.json?user=codexe` until a replay is already in the archive or is older than the start date. Download `.json` and `.log` for each new one. Run when the app opens and every N minutes while the server runs (N **unknown**; 15 is a guess).
   - **Private replays:** included. **Unknown:** how to list and fetch them. Research before building. Never store the Showdown password ([[ADR-0006-replay-archive]]).
3. **Userscript (stage 2).** Runs on play.pokemonshowdown.com. When a battle ends, it sends the full battle log, format, players and room id to `POST http://localhost:<port>/api/ingest`. The server stores it and removes duplicates against replays the poller already fetched (match on room id / battle id).
   - **Unknown:** the exact client hook for "battle ended" and whether the browser allows a request from Showdown's page to localhost. Allow that origin in FastAPI's CORS settings for `/api/ingest` only.
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
