---
title: ADR-0006 Local replay archive
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/data]
---

# ADR-0006: Save every game from now on in a local archive

## Context
- The user wants the app to "pull user data and list each game with some details, and also auto save all replays" ([[2026-11-22-interview-round-1]]).
- Only uploaded games exist on Showdown's replay server ([[data-sources]]). Public replays leave the search results fast: 3,000 Champions OU replays covered only about 10 days ([[2026-11-22-research-findings]]).
- Round 2: the user chose "uploaded now, all later", and added: "don't worry about prevous games. just send every finished game to the app going frward". Private replays are included. Every format is saved and listed ([[2026-11-22-interview-round-2]]).

## Decision
- **No backfill.** The archive starts on the day sync is first turned on. Older games are not fetched.
- **Stage 1: poller.** Fetches new uploaded replays (public and private) for user `Codexe` with an upload time after the start date.
- **Stage 2: userscript.** A small userscript on play.pokemonshowdown.com sends the full log of every finished battle to the local server, whether or not it was uploaded. Once it works, it is the main way games arrive, and the poller becomes a backup.
- **Storage.** A local SQLite database indexes every game. Each game's raw `.log` (and `.json` when it came from the replay server) is stored as a file next to it. Files are never deleted. Every format is stored.

## Why the userscript also matters for private games
The userscript runs inside the user's own logged-in browser tab, so it captures private games **without the local app ever holding the Showdown password or session cookie**. The poller needs a way to read private replays. That method is **unknown** and must be researched before it is built ([[open-questions]]). The app must never store the user's Showdown password.

## Options considered
- **Poll uploaded replays only:** simple, but misses games that were never uploaded.
- **Poller, then userscript (chosen):** catches every game from now on.
- **Fetch on demand only:** loses games once they drop off the search.

## Consequences
- The archive also serves as training data for [[spec-eval-model]].
- The userscript adds a small piece outside the web app ([[ADR-0001-local-web-app]]). It only sends logs to localhost and draws no UI on Showdown's page.

## Related
- [[spec-replay-sync]] · [[data-sources]] · [[ADR-0001-local-web-app]]
