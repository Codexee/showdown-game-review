---
title: First real-browser game with auto-upload (userscript v0.2.0)
type: raw
source: app data and server log, read by Claude 2026-11-23 ~12:50 EST
tags: [area/data]
created: 2026-11-23
---

Game `gen9randombattle-2718385244`, Codexe vs jencast, rated ladder (Codexe 1729 → 1747, win).

- Started 12:33:25 EST. v0.3.0 (private uploads) was committed at 12:41:51, so the script that ran this game was **v0.2.0**: upload with the room's own privacy, no `/hidereplay`.
- 12:41:54: `/api/ingest` stored the browser copy, and in the same second the replay server shows `uploadtime` 1795455714. So the script's `/savereplay silent` was accepted on the main server, in a rated game. The replay is **public** (`private: 0`; `<id>.json` returns 200), as v0.2.0 was meant to do.
- The app on port 8765 then was the server started at 09:23, from code older than `/api/ingest-uploaded`. Its 8 s and 30 s checks got 405, which the script treats as "not found" and keeps going. The old server's own poller upgraded the game (inputlog stored) and auto-analysis finished at 12:43:30. No clicks.
- 12:43:56: the 120 s check reached the restarted server (new code) and got `found: true` (200), then stopped.
- The log has `|player|p1|` lines in the middle (a disconnect and rejoin); capture still worked.
- Not yet known: whether a popup appeared, and whether Chrome showed a Local Network Access prompt (ask the user).
