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

- **Research round 2** ([[2026-11-22-research-round-2]]): solved all four research items from the open questions. Big find: random-battle replays include an inputlog with seeds and the Showdown commit, so full hidden information may be rebuildable ([[ADR-0009-randbats-full-info-reconstruction]], proposed). Added [[ADR-0008-python-313]].

- **Stage 2a built** ([[module-map]]): uv venv on 3.13; FastAPI backend (archive, poller, imports, API); Vite/TS game list page; 18 tests pass. Fixed a team-parsing bug ([[2026-11-22-bug-forme-change-team]]). Live check: the profile loaded (most-played: gen8randombattle, gen9randombattle), the first sync set the archive start to 2026-11-22 06:37, and two older games were added by URL. Codexe's newest upload is a Champions VGC Reg M-C game.

- **Stage 2b built:** userscript plus ingest routes, an install panel in the app, and [[ADR-0010-local-api-origin-guard]]. Fixed two problems found while designing: the poller stopped at the first known game, which would hide uploads once the userscript adds games first (now a high-water mark, with a regression test); and uploaded `.json` ids could escape `data/` (now validated). 27 Python + 7 Node tests pass; an end-to-end run against a throwaway server worked. Not yet run on the real Showdown site.

- **Rebuild prototype** ([[2026-11-22-rebuild-prototype-results]]): 61/61 `gen9randombattle` replays rebuilt exactly at their commit; a wrong commit gives visible and silent errors. ADR-0009 is ready for the user's OK. Also fixed `parse_replay_ref` to accept side-server ids (`impulse-…`, `smogtours-…`).

## Lesson
Facts that exist only in a chat transcript are easy to lose when a question is skipped or work moves to a new session. Write answers to `raw/` as soon as they arrive ([[ADR-0003-vault-as-memory]]).

## Next
- User: install the userscript and play one game ([[open-questions]] #1).
- Prototype the inputlog rebuild on a few replays ([[open-questions]] #2).
