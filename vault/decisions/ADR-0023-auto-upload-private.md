---
title: ADR-0023 Auto-uploaded replays are private
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/data]
---

# ADR-0023: Auto-uploads are private (`/hidereplay` at the start); amends ADR-0022

## Context
- [[ADR-0022-auto-upload-replays]] uploaded with the room's own privacy, so a game in a public room became a public replay under your name ([[open-questions]] #16).
- The user chose private ([[2026-11-23-auto-upload-private]]).
- Showdown source (`server/chat-commands/core.ts`, `server/room-battle.ts`, master, read 2026-11-23): `/hidereplay` needs the player rank (`checkCan('joinbattle')`, "Requires: ☆ ~"). It sets `room.hideReplay`. It fails only in force-public tournaments or when the replay is already hidden. It posts "<name> hid the replay of this battle." to the room. At the end, a `hideReplay` room becomes private (`modjoin '%'`) and is renamed `…-<password>pw`. `uploadReplay` then saves the replay with `private: 1` and that password.

## Decision
This replaces ADR-0022 decision 2. The rest of ADR-0022 stands.
1. When a battle you play reaches `|start`, and auto-upload is on, the userscript sends `/hidereplay` once. It doesn't send it if the log already shows the notice (a reload mid-battle).
2. At the end, it follows the rename to `…-<pw>pw` and uploads with `/savereplay silent` under that id. `/api/ingest-uploaded` then fetches `<id>-<pw>pw.json` with no login.
3. If the script only sees the game after the end (no `|start` seen live), it sends `/hidereplay` just before `/savereplay silent`. The replay is still private, but there is no rename, so the script doesn't know the password. After the three checks miss, the private replay list (`searchprivate`) finds it.
4. With auto-upload off, nothing is hidden and nothing is uploaded.

## Consequences
- Your opponent sees "Codexe hid the replay of this battle." at the start of each game. Spectators can't join after the end (Showdown's own rule for hidden replays).
- If you click "Upload and share replay" yourself, that replay is private too. You can still share it by its link, which carries the password.
- In a force-public tournament, `/hidereplay` is refused and the replay is public. That is Showdown's rule.
- Unknowns are in [[open-questions]] #17.

## Related
- [[ADR-0022-auto-upload-replays]] · [[spec-replay-sync]] · [[ADR-0006-replay-archive]]
