---
title: Move review, sampled worlds vs real sets
type: raw
source: local runs, 2026-11-22
tags: [area/model]
created: 2026-11-22
---

# Move review: sampled worlds vs real sets (2026-11-22)

Model `main@9000`, top 6 choices per side. "Perfect" = ADR-0014 (real hidden sets, 16 seeds per pair). "Worlds" = ADR-0015 (16 sampled worlds per graded side, one seed each). Games: 12 random `gen9randombattle` replays from `data/train/inputlog` (15–35 turns, all at Showdown commit `ac7b7da0f9`), plus Codexe's `gen9randombattle-2705718015`.

## Codexe's game
- Perfect 31 s, worlds 77 s. Accuracy (Codexe / opponent): perfect 93.2 / 96.6, worlds 94.1 / 96.4.
- 45 of 50 verdicts the same; 1 choice flagged in one mode only (T8 switch to Venusaur: inaccuracy 6.3 → good 4.2). Regret difference mean 0.30, max 2.7. The T18 mistake stands.

## 12 games, worlds vs perfect
- 608 graded choices. Same verdict: 482 (79%). Flagged (inaccuracy or worse) in one mode only: 36 (6%).
- Regret difference: mean 0.82 points, max 18.7.
- Time per game: perfect 19–40 s, worlds 48–101 s (about 2.5×).
- Accuracy changes per player ranged from −3.6 to +3.9 points.
- Largest changes:
  - `2714497599` T26 p2 Flip Turn: perfect best 0.0 → worlds mistake 18.7 (best Hydro Pump).
  - `2714497599` T5 p1 Wave Crash: good 1.2 → mistake 14.4.
  - `2717695145` T2 p1 switch to Gothitelle: good 1.5 → mistake 13.0.
  - `2717695145` T14 p2 Encore: mistake 11.0 → good 4.2.
  - `2716220430` T13 p1 Ice Spinner: mistake 10.7 → good 4.2.
- Changes go both ways: some choices look worse once the grader stops knowing the opponent's real set (they relied on luck in the hidden sets), others look better (they were reasonable given what could be seen).

## Noise check: worlds 16 vs 32
- First 3 of the 12 games. The 32-world run shares its first 16 worlds with the 16-world run, so this understates noise between fully independent runs.
- 184 graded choices. Same verdict: 178 (97%). Flagged in one only: 3 (2%). Regret difference mean 0.24, max 4.3.
- For comparison, ADR-0014's perfect mode at 16 vs 32 seeds: 50 of 50 the same, max 0.59 ([[2026-11-22-stage6-results]]).

## Reading
- Worlds-vs-perfect differences (6% flag flips, mean 0.82) are about 3× the worlds noise (2%, 0.24), so most of the change comes from hiding the opponent's sets, not from sampling.
