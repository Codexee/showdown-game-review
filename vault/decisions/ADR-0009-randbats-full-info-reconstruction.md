---
title: ADR-0009 Rebuild full-information randbats games from inputlogs
type: adr
status: proposed
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model, area/data]
---

# ADR-0009: Rebuild full-information Gen 9 Random Battle games from replay inputlogs

> [!success] Prototype 2026-11-22: 61/61 exact rebuilds
> Proposed for acceptance; waiting on the user ([[open-questions]]). Evidence: [[2026-11-22-rebuild-prototype-results]].

## Context
- For random formats, the replay JSON includes the **inputlog**: the Showdown commit hash (`>version`), the battle seed, each player's team seed, and every choice ([[2026-11-22-research-round-2]]).
- A normal replay log shows only what was revealed during the game. Metamon has to guess hidden sets when it rebuilds each player's view ([[bot-landscape]]).

## Decision (proposed)
- For each archived random-format replay, run Showdown's simulator **at the exact commit named in `>version`** on the inputlog. This reproduces both full teams (moves, item, ability, Tera type, level, EVs, IVs) and the whole battle, including the omniscient log.
- **Validate** every rebuild by comparing it with the replay's public log, after dropping server-only lines (list in the prototype results). Uploaded replay logs use the omniscient channel, so compare against channel -1. Drop any replay that doesn't match.
- **Never** rebuild at a different commit, even a close one: in the prototype, 1 of 56 wrong-commit runs matched the public log but had a wrong hidden set ([[2026-11-22-rebuild-prototype-results]]).
- Keep a cache of built Showdown checkouts keyed by commit (`git worktree` per commit from one blobless clone). Commits change about every 1–2 weeks on the main server, so a month of replays needs only a handful of checkouts.
- Training uses each turn's **partial view** as input and the **full state** as extra targets (opponent sets, hidden HP) ([[spec-eval-model]]).
- At review time (no inputlog for the opponent), use pkmn randbats stats as priors ([[data-sources]]).

## Evidence (prototype, 2026-11-22)
- 61 replays (3 commits): 61/61 exact log matches at the right commit; 56/61 at a wrong commit, including 1 silent hidden-set error.
- ~57 ms per replay including Node start; ~5 s and ~200 MB to set up each commit.
- Side servers (e.g. `impulse-…`) run their own commits; filter by server prefix or accept a few extra checkouts.

## Risks
- Disk: ~200 MB per commit. Share `node_modules` between checkouts or delete old checkouts after their replays are processed.
- If Showdown stops publishing inputlogs, this source stops; the archive keeps what it already has.
- Doesn't apply to VGC Reg M-C (no safe inputlog). That stage needs the partial-view method plus team sheets.

## Related
- [[spec-eval-model]] · [[data-sources]] · [[formats]] · [[2026-11-22-rebuild-prototype-results]]
