---
title: "Plan: training run v1.2 (value overfitting)"
type: spec
status: active
tags: [area/model]
updated: 2026-11-22
---

# Plan: training run v1.2 (fix value overfitting)

The user asked for this plan on 2026-11-22. **Tests started 2026-11-22** after the user's go-ahead ([[2026-11-22-v12-tests-go]]); the overnight run still waits for a go.

## Problem
In the `main` run the value loss was lowest at step 9,000 (epoch 1.2, 0.5755) and then rose to 0.6172 by epoch 2.7. Over the same steps the fitted temperature went from 0.97 to 1.65 (the model grew overconfident), while the policy kept improving ([[2026-11-22-main-run-results]]).

**Cause:** every turn of a game shares one label (who won). 15.8M samples are only 672k independent outcomes, so after about one pass the model starts to memorise games. The validation split is by game (`training/build_dataset.py` `is_val`), so this is real overfitting, not leakage.

## Target
Beat the installed `main@9000` on the pinned bank of future games (log-loss 0.5854, accuracy 67.4%; 3,709 games) in the paired gate ([[spec-eval-model]]). The overnight script already installs only if the gate doesn't call the new model worse.

## Levers
1. **More games (largest lever).** The downloaded dataset has 563k games from 2025 and 713k from 2024, besides the 676k from 2026 used so far (counted from `data/hf/*.parquet`, 2026-11-22). Adding 2025 gives about 1.24M games and 29M samples. Risk: Random Battle sets and the meta change over time, so older games may teach slightly wrong things. Test D measures this.
2. **Stronger regularisation:** dropout 0.1 → 0.2 and weight decay 0.05 → 0.1 (current values: `training/model.py`, `training/train.py`).
3. **Value-loss schedule:** keep the value weight at 1 for the first epoch, then lower it (cosine to 0.2), so the policy and auxiliary heads keep training without the value head memorising.
4. **Keep:** `best.pt` chosen by value loss, temperature fit, the paired gate.
5. **Not now:** TD / bootstrapped value targets (lower-variance labels, but a bigger change); training on the 14-day collected games. Those stay test-only, because the pinned bank comes from them and they are the only "future" games we have.

## Code changes (built 2026-11-22)
- `train.py`: `--dropout`, `--value-weight-floor` (weight 1 for epoch 1, then cosine to the floor); `value_weight` logged in `metrics.jsonl`.
- `build_dataset.py`: `--ranges` (several date ranges in one dataset, for the data-mix test).
- `overnight.sh`: `SINCE`, dropout, wd and the schedule as variables (not yet; after the tests).
- `training/tests_v12.sh`: the four tests and gates, resumable.

## Small tests first (CLAUDE.md rule; about 4.5 h, background)
Each test runs 4 epochs on the `medium` dataset (138k games since 2026-08-01, about 12 minutes per epoch), where overfitting shows up sooner. Each is scored on the pinned bank.

| Test | Data | Settings | Question |
|---|---|---|---|
| A | medium | current | baseline: when does the value loss turn up? |
| B | medium | dropout 0.2, wd 0.1 | does regularisation delay or lower the turn? |
| C | medium | B + value schedule | does the schedule keep the value loss flat while the policy improves? |
| D | medium + 138k games from 2025-07..09 | B | do older games help or hurt on future games? (twice the games, so about 8 min more per epoch) |

Readout: best value loss and its epoch, pinned-bank log-loss, gate A vs B, B vs C, B vs D. Also check that step time on a dataset bigger than RAM stays near 0.46 s.

## Overnight run (after the tests; 9 h, [[ADR-0005-overnight-training-budget]])
- Data: games since 2025-01-01 if D helps, else 2026 only.
- Settings: the winner of A/B/C; d=256, 6 layers (unchanged); bs 2048, lr 4e-4.
- About 14k steps per epoch at 1.24M games, so roughly 4.5 epochs in 9 h; `best.pt` keeps the best value step.
- Then: test on the pinned bank, paired gate vs `main`, install if not worse. Record results in `raw/` and [[spec-eval-model]].

## Needs from the user
- The Mac must stay awake: lid open, or on power with an external display. Clamshell sleep on battery pauses runs ([[environment-quirks]]).
- A go-ahead for the tests (about 4.5 h), then a separate go-ahead for the overnight run once the tests are read.

## Related
- [[spec-eval-model]] · [[2026-11-22-main-run-results]] · [[ADR-0005-overnight-training-budget]] · [[ADR-0012-training-data-v1]]
