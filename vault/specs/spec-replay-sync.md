---
title: Spec: replay sync and game list
type: spec
status: draft
tags: [area/data, area/ui]
updated: 2026-11-22
---

# Spec: replay sync and game list (draft)

Source request: "Should pull user data and list each game with some details, and also auto save all replays." ([[2026-11-22-interview-round-1]]) Storage choice: [[ADR-0006-replay-archive]].

## User story
I enter my Showdown username once. The app shows my ratings and a list of my games, newest first. Every game is saved on my Mac, so I can review it after it drops off Showdown's search.

## Functions
1. **Profile.** Fetch `users/<userid>.json`: rating, GXE and games per format ([[data-sources]]). Refresh on open.
2. **Sync.** Page through `search.json?user=<userid>` until reaching a replay already in the archive. For each new one, download `.json` and `.log`. Run on app open and every N minutes while the server runs. (N **unknown**; 15 is a guess.)
3. **Archive.** Store the raw files under `data/replays/<format>/<replay-id>.{json,log}` and a row in SQLite. Never delete. Re-running sync must not create duplicates.
4. **Game list** (in the UI) shows per game: date, format, opponent, result (win/loss), rating before/after if the log has it, turn count, both teams as sprite icons, and an "analyzed" badge once the model has scored it. Filter by format, result and opponent.
5. **Manual import** (maybe): paste a replay URL, or drop a saved `.log`/`.html` file. Not decided ([[open-questions]] #7).

## Details to get right
- Send a browser-like user agent and add a short delay between requests ([[environment-quirks]]).
- The parser in [[spec-eval-model]] reads files from the archive, not from the network.
- Both players' names are in the log; mark which side is the user.

## Not decided
See [[open-questions]] #3 (username), #4 (games that were never uploaded), #5 (private replays), #6 (which formats to list).

## Done when
- A fresh sync of a real username stores every listed replay once, and a second sync adds nothing.
- The game list shows the fields above for those games.

## Related
- [[data-sources]] · [[spec-review-app]] · [[architecture]]
