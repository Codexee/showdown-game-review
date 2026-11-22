---
title: Session log 2026-11-22
type: log
date: 2026-11-22
tags: [area/vault]
---

# Session log: 2026-11-22

- **Main planning session** (transcript f510bfb3): found local Showdown bots; copied 33 skills from PatriotHacks into `.claude/skills/`; added the every-prompt skill hook; checked hardware; researched Champions formats, Smogon stats, replay API and bots ([[2026-11-22-research-findings]]); ran interview round 1 ([[2026-11-22-interview-round-1]]).
- **Side session** (transcript 8ebed2c6, forked): explained why a web app comes before an extension. Reasoning now in [[ADR-0001-local-web-app]].
- **This session** (transcript 15119347): the user sent the input answer they had skipped by accident, plus the pixel-art request and the second-brain guide. Recovered the round-1 answers and research from the main session's transcript, because the new session did not have them. Built this vault, wrote ADR-0001 to ADR-0006 and the three specs, searched for a pixel-art tool (found SpriteCook), ran `git init` and made the first commit.

- **Same session, later:** interview rounds 2 and 3 ([[2026-11-22-interview-round-2]]). Settled: standard Gen 9 Random Battle; save every finished game from now on, with no backfill, private games included; list all formats; URL, file and team-paste input; keep 1.5% for VGC; FastAPI + Vite/TS. Accepted [[ADR-0006-replay-archive]], added [[ADR-0007-app-stack]]. What's left in [[open-questions]] is mostly research.

## Lesson
Facts that exist only in a chat transcript are easy to lose when a question is skipped or work moves to a new session. Write answers to `raw/` as soon as they arrive ([[ADR-0003-vault-as-memory]]).

## Next
- Research the open items in [[open-questions]] (private replays, userscript hook, Python version, randbats set data).
- Then start [[roadmap]] stage 2a ([[spec-replay-sync]]).
