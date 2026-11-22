---
title: ADR-0006 Local replay archive
type: adr
status: proposed
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/data]
---

# ADR-0006: Keep every replay in a local archive

## Context
The user wants the app to "pull user data and list each game with some details, and also auto save all replays" ([[2026-11-22-interview-round-1]]). Public replays leave the search results fast: 3,000 Champions OU replays covered only about 10 days ([[2026-11-22-research-findings]]). Only uploaded games exist on the server ([[data-sources]]).

## Decision (proposed)
- A local SQLite database indexes every game; the raw `.log` (and `.json`) of each replay is stored as a file next to it. Files are never deleted.
- A poller fetches the user's new replays on a schedule and when the app opens.
- Stage 2, if the user wants it: a small userscript on play.pokemonshowdown.com sends each finished battle's log to the local server, so games that were never uploaded are saved too.

## Options considered
- **Poll uploaded replays only:** simple, no browser add-on, but misses games that weren't uploaded.
- **Poll plus userscript (proposed as stage 2):** catches every game, but adds a small browser add-on.
- **Only fetch on demand:** loses games once they drop off the search.

## Consequences
- The archive doubles as training data for [[spec-eval-model]].
- Waits on [[open-questions]] #3–#6 before it is accepted.

## Related
- [[spec-replay-sync]] · [[data-sources]] · [[ADR-0001-local-web-app]]
