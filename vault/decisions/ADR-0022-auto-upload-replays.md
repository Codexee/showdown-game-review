---
title: ADR-0022 The userscript uploads each game you play as a replay
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/data]
---

# ADR-0022: Auto-upload each finished game with `/savereplay silent`

## Context
- Move review needs the inputlog (`server/review/jobs.py` `supported()`). The browser never sees it. Showdown saves it only with an uploaded replay, and the replay API returns it only for random formats ([[2026-11-22-research-round-2]]). So a game you didn't upload could not be reviewed.
- The user asked for analysis to need no input after a game ([[2026-11-23-auto-upload-replays]]).

## Decision
1. When a battle that **you played** (your name is on a `|player|` line) ends, the userscript waits 4 s for the rating lines, sends the log to `/api/ingest` as before, and then sends `/savereplay silent` to the room. This is the client's "Upload and share replay" command without its popup. The command goes through the room's own `send`, or the client's `send(text, roomid)` if the room object is missing. Spectated games and unfinished games are never uploaded.
2. Privacy is Showdown's: the server makes the replay private when the room is private (hidden or invite-only battle, or `/hidereplay`). The script never changes it. When a hidden battle is renamed to `…-<pw>pw` at the end, the script follows the rename, so it knows the password.
3. Then the script calls `POST /api/ingest-uploaded {roomid}` at 8 s, 30 s and 120 s after the upload, and stops at the first `found: true`. Each call makes at most one replay-server request (`<id>[-<pw>pw].json`). On a hit the server upgrades the userscript copy, which adds the inputlog, and `on_saved` queues auto-analysis. If all three miss, the script lists private replays once (`searchprivate`). The 5-minute poller covers anything left.
4. Switch: Tampermonkey menu → "Auto-upload replays" (`GM_setValue('autoUpload')`). Default **on**. Off means today's behaviour.
5. App not running: the Showdown upload still happens. `/api/ingest` and `/api/ingest-uploaded` are queued (`GM_setValue`) and sent on the next page load.

## Consequences
- Every game you play in a public room becomes a **public replay**, searchable under your name on replay.pokemonshowdown.com. Before, only games you uploaded were public. Whether auto-uploads should be private by default is [[open-questions]] #16.
- VGC and other non-random formats: the replay is uploaded and saved (upload time, private flag, server log), but it has no inputlog and doubles has no model, so there is no move review. Auto-analysis reports "unsupported" and does nothing.
- `archive.needs()` now treats a userscript copy as needing the replay server only until it has an upload time. Before, an upgraded copy looked "needed" forever.
- Not yet tried in a real browser ([[open-questions]] #1).

## Related
- [[spec-replay-sync]] · [[ADR-0006-replay-archive]] · [[ADR-0010-local-api-origin-guard]] · [[module-map]]
