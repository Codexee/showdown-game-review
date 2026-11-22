---
title: Stage 6 move review, first results
type: raw
source: local runs, 2026-11-22
tags: [area/model, area/ui]
created: 2026-11-22
---

# Stage 6 move review: first results (2026-11-22)

Measured on this Mac with model `main@9000` and Codexe's game `gen9randombattle-2705718015` (Showdown commit `cbdc8519ef`), 16 seeds per pair, top 6 choices per side.

## Bugs found while building
- `State.deserializeBattle` changes the snapshot object it is given. Reusing one parsed snapshot made 1,319 of 1,352 cells invalid. Fix: store each turn-start snapshot as a JSON string and parse it again for every cell.
- Played choices come from the inputlog in client form (`move uturn`), not slot form (`move 1`). Fix: `normalize()` in `tools/review-engine.cjs`. After the fix, all 50 played choices matched an option.
- `AnalyzeBody` was defined inside `create_app`; with `from __future__ import annotations` FastAPI could not resolve it and ignored the request body, so `seeds: 1` was accepted. Fix: module-level model. Found by `test_analysis_api_gates`.

## Result for the test game
- 25 turns, 30.5 s.
- Codexe: accuracy 93.2; 14 best, 7 good, 2 inaccuracies, 1 mistake; luck −20.6 points.
- charizardslayer1: accuracy 96.6; 18 best, 6 good, 1 inaccuracy; luck +20.6 points.
- Graded choices:
  - T8 Codexe Dazzling Gleam (best: switch to Venusaur), 6.3 points, inaccuracy.
  - T14 opponent Mud Shot (best: Wish), 6.1, inaccuracy.
  - T15 Codexe Shadow Ball (best: Will-O-Wisp), 7.0, inaccuracy.
  - T18 Codexe switch to Venusaur into Sawsbuck's Swords Dance (best: Will-O-Wisp), 14.6, mistake.
- Biggest luck swings for Codexe: T20 −14.3 (Horn Leech), T19 −5.2, T2 −3.6.

## Stability
- 16 vs 32 seeds: the same verdict on 50 of 50 graded choices; largest regret difference 0.59 points.

## Checks
- API: `POST /api/games/{id}/analysis` built the sim checkout for the commit on first use and finished in 34 s. The VGC fixture is reported as unsupported.
- Browser: summary cards, turn-list marks (`?!`, `?`), the review box per turn, and the graph marker on T18 render in dark mode at desktop and phone width (no sideways scroll).
- Tests: 91 Python tests pass, including an engine test against the real sim build (skipped when the build is missing).
