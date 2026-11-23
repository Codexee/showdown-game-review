---
title: Answers to open questions 2–5 (side servers, poll interval, UI framework, SpriteCook)
type: raw
source: user message in chat, 2026-11-23
tags: [area/data, area/ui]
created: 2026-11-23
---

User, verbatim:

"open questions

2. no, main server
3. 5 mins
4. not relevant anymore
5. yes"

Reading recorded by Claude, against [[open-questions]] as of 2026-11-23:
- #2 Side-server replays: no; main-server ids only (already what `training/collect.py` does).
- #3 Replay poller interval: 5 minutes (was 15).
- #4 Frontend UI framework: not relevant anymore (the app was built in plain TypeScript, no framework).
- #5 Install SpriteCook: yes.
