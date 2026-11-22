---
title: ADR-0005 Overnight training budget
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model]
---

# ADR-0005: One training run is overnight, 8–12 hours

## Context
The user wants training on this Mac to save Claude usage: a small test first, then the full run with little interaction. They chose "Overnight, 8–12 h" ([[2026-11-22-interview-round-1]]). Hardware: [[environment]].

## Decision
- Size the model and dataset so one full run finishes in 8–12 h on the M5 Pro GPU (MPS).
- Every full run is preceded by a short test run (minutes) that checks loss goes down, memory fits and checkpoints save.
- Runs start in the background, save checkpoints often, and resume after a stop. Claude checks the log only at the end.

## Consequences
- The estimate from the planning session was a 10–25M-parameter model on replays plus a few hundred thousand self-play games. (unverified: not yet measured)
- Keep the Mac on AC power with keep-awake on.

## Related
- [[spec-eval-model]] · [[environment]]
