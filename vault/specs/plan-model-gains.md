---
title: "Plan: eval gains beyond more training"
type: spec
status: active
tags: [area/model]
updated: 2026-11-23
---

# Plan: eval gains beyond more training (model-testing stage)

The user asked on 2026-11-23 for a plan that doesn't stay boxed into training runs, because larger gains may be elsewhere ("plan then continue"). This stays inside the current model-testing stage ([[roadmap]] item 7, [[2026-11-22-direction-codex-review]]).

## Why
- The first free gain came from inference, not training: averaging both players' views cut log-loss by 0.0026 with no retraining ([[ADR-0016-two-view-scoring-strict-gate]]). Regularisation in test B changed nothing on future games under the same scoring.
- Jaxcalibur: "most of the strength is the network", but search adds ≈100–150 Elo ([[2026-11-22-prior-art-jaxcalibur-mikumiku]]). The move review already runs that kind of one-turn search for every turn; the eval bar doesn't use it.

## Candidates, cheapest first
Each one is scored on the pinned bank (two-view, paired, 90% bands over games), against `main@9000` at 0.58285.

| # | Idea | Cost | Needs training? |
|---|---|---|---|
| 1 | **Ensemble** of runs we already have (`main`, v12a–d): average their predictions | seconds, from saved predictions | no |
| 2 | **Calibration by rating and phase:** the bank's median rating is 1427 against 1676 in training ([[2026-11-22-p0-ab-results]]); check whether one temperature fits all, refit on validation if not | minutes | no |
| 3 | **Symmetry averaging:** score each position with the bench order shuffled and average, if the network isn't already order-blind | one inference pass per shuffle | no |
| 4 | **One-turn search as the eval:** the value of the solved choice matrix at the turn start (what the move review computes) instead of the raw network | ≈1 min per game on the CPU; a sample of games | no |
| 5 | **Weight averaging** of checkpoints near the value minimum (needs saved checkpoints; only best and last exist now) | small code change to keep checkpoints | next run |
| 6 | **Distil** the ensemble or search values into one network (a teacher signal with less noise than one win/loss label per game) | a training run | yes, later |

Still training-side, after these: game-balanced value sampling ([[plan-run-v12]] item 4), history tokens and matchup damage calcs ([[benchmark-best-in-class]]), the "public" mask ([[open-questions]] #8).

## Outside model testing (recorded, not now)
- Move-review fairness (dice averaged inside each cell, one strategy across worlds, unseen bench sampled): probably the largest gain for grade quality ([[2026-11-23-codex-review]] finding 6). It belongs to the move-review stage.

## Results
Raw numbers: [[2026-11-23-v12-tests-and-eval-gains-results]]. Against `main@9000` two-view (0.58285; 0.5851 on the 199 search games):
1. Ensemble: **worse** (other runs are weaker and too similar).
2. Calibration by rating / phase: **≈0**.
3. Bench-order symmetry: **0 by design** (the network is order-blind).
4. **One-turn search: the largest gain found.** Blend 75% search + 25% network, worlds mode (fair): **−0.0083** [−0.0118, −0.0048], about 3× the two-view gain; perfect mode −0.0098. Search alone: −0.0047, band crosses zero. Cost: the move review already computes it (141 s per game in worlds mode).
- Also tried: the players' rating gap. **No signal** (ladder gaps are tiny; the higher-rated player wins 50.3%).

## Next steps, ranked (2026-11-23)
1. **Eval bar from search after "Analyze":** once a game's move review exists, show the 75/25 blend instead of the raw network. No training; −0.008 measured. Blend weight chosen on the test games; confirm on a fresh sample. Small server + UI change.
2. **Overnight run** on 2025 + 2026 with C's settings ([[plan-run-v12]]): the data lever, −0.008 between B and D at small scale.
3. **Distil search into the network:** train the value head on search values (or the blend) as soft targets. Each position gets its own target, not one win/loss per game, which also attacks the overfitting cause. Needs search values for many games (≈2 min per game; 5 parallel ≈ 3,000 games per night).
4. Data hygiene: drop custom-rule games ([[2026-11-23-bug-custom-rules-randbats]]).
5. Later training-side: history tokens, matchup damage calcs, game-balanced value sampling.

## Related
- [[plan-run-v12]] · [[spec-eval-model]] · [[ADR-0016-two-view-scoring-strict-gate]] · [[2026-11-23-codex-review]]
