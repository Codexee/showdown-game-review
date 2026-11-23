---
title: Request: auto-upload each finished game so analysis needs no input
type: raw
source: user request relayed by the parent Claude session, 2026-11-23
tags: [area/data]
created: 2026-11-23
---

User, verbatim:

"make the userscript automatically upload the replay so that analysis requires no input after finishing a game"

Constraints set with the request (by the parent session): use Showdown's normal client behaviour only; no credentials beyond the existing browser login; private replays stay private if the room is private; keep a switch to turn auto-upload off; keep the queued sends when the app isn't running; move review stays Gen 9 Random Battle singles only, so say what happens for VGC.

## Research done for it (2026-11-23, Showdown source on GitHub, master)
Server (`smogon/pokemon-showdown`):
- `server/chat-commands/core.ts`: `savereplay` (alias `uploadreplay`) needs only that the room has a battle. It does not check that the sender is a player or that the battle has ended. Its only targets are `forpunishment` and `silent`. No throttle in the command itself.
- `server/rooms.ts` `uploadReplay`: privacy comes from the room: `isPrivate = settings.isPrivate || hideReplay`, so `hidden` is 1 for a private room and 0 otherwise. The password is the room id's `-<pw>pw` suffix, or a new one. The inputlog is saved in both upload paths (`battle.inputLog`). With `silent`, `connection` is cleared, so the user gets no popup. No `|queryresponse|savereplay|` is sent any more.
- `getReplayData`: `battle-<format>-<n>-<pw>pw` → id `<format>-<n>`, password `<pw>`.
- `hidereplay`: sets `room.hideReplay = true`. At battle end (`room-battle.ts`), a `hideReplay` room is made private with `setPrivate('hidden', password)`, which renames the room to `…-<pw>pw`.
- `room-battle.ts` `end()`: re-uploads silently if `replaySaved || Config.autosavereplays`. The value of `Config.autosavereplays` on the main server is not in the source.
- No per-user "private replays by default" setting was found. Privacy is per room: hidden or invite-only battles, and `/hidereplay`.

Client (`smogon/pokemon-showdown-client`):
- Old client (`src/oldclient/client-battle.js`): the "Upload and share replay" button runs `saveReplay: this.send('/savereplay')`. A room's `send(data)` is `app.send(data, this.id)`, and `app.send(data, room)` sends `room|data`. `app.rooms` is keyed by room id. `|noinit|rename|<newid>|<title>` makes it call `renameRoom`.
- New client (`src/panel-battle.tsx`): the button is `data-cmd="/savereplay"`. `PS.send(msg, roomid)` sends `${roomid}|${msg}`. `PSRoom.send(msg)` sends to its own room. `PS.rooms` is keyed by room id. It handles the `noinit` `rename` message too.
- The `uploadprivacy` pref is for teambuilder team uploads, not replays.
