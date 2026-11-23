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

## Changes from the Codex review (items 1–3 done 2026-11-23, [[ADR-0016-two-view-scoring-strict-gate]]; 4–5 wait on the user)
Source: [[2026-11-23-codex-review]]. Items 1–3 are checked; 4–5 are test-design advice.
1. **Fix the install gate in `overnight.sh` before any overnight run.** Fresh run name (not `main`), dataset rebuilt or checked against `SINCE`, B/C settings passed through, and install only on "b is better" or an explicit rule; "no clear difference" or a skipped gate keeps `main`.
2. **Two-view scoring** for the eval bar, `test_model` and the gate, the same as the move review's leaf: measured −0.0026 log-loss on `main` with no retraining.
3. **Strict pairing in `compare_runs`:** fail if the two prediction files don't have the same keys.
4. **A game-balanced value test** (a fifth small run): sample games evenly, a few positions per game for the value loss, dense policy labels. It tests the "one label per game" diagnosis directly.
5. **Read C and D carefully:** C's schedule depends on the configured epoch count (4 here, 8 in the overnight script). D changes data age, game count and update count together, so a D win doesn't mean all of 2025 helps. The pinned bank has now informed several choices; keep a later window of collected games for one final check against `main`.

### Readout so far, two-view scoring (2026-11-23)
- A vs B: log-loss 0.59736 vs 0.59734, no clear difference (single view had B ahead by 0.0017, band crossing zero). So far regularisation changes the validation curve's shape (B stays flat to epoch 4) more than the score on future games.
- `main` vs B: B worse by 0.0145, band [+0.0103, +0.0186]. `main` two-view: 0.58285.
- The overnight script's settings defaults are still the old ones (dropout 0.1, wd 0.05, no schedule, 4 epochs); set them from the test winner when the overnight run is approved.

### Test results (2026-11-23, [[2026-11-23-v12-tests-and-eval-gains-results]])
- **B (dropout 0.2, wd 0.1) = A** on future games (−0.00002). Regularisation flattens the validation curve but doesn't improve predictions.
- **C (value-weight schedule) beats B** by 0.0018 [−0.0033, −0.0003].
- **D (twice the games, half from 2025-07..09) beats B** by 0.0079 [−0.0114, −0.0044] and C by 0.0061. More games is the largest training lever, and older games help. D had twice the updates too, but B did not gain from its extra updates on the same games (A and B plateau or rise after epoch 2–3), so the gain is the data (Codex's caveat noted, not fully separated).
- All four trail `main` (D by +0.0066), which trained on 672k games.

### Overnight run, recommended (waits for the user's go-ahead)
`RUN=v12 SINCE=2025-01-01 DROPOUT=0.2 WD=0.1 VW_FLOOR=0.2 EPOCHS=3 HOURS=9 ./training/overnight.sh`
- Data: 2025 + 2026, about 1.24M games, ≈29M samples (estimated from `full`: 23.5 samples per game), ≈30 GB on disk (448 GB free). Larger than RAM (24 GB); step time is the open risk (0.47–0.65 s measured), so 3 epochs ≈ 5.5–7.7 h, and the 9 h ceiling stops it if slower.
- Settings: C's (the schedule needs dropout 0.2 / wd 0.1 too; both were in C).
- Install: only if the two-view gate says better than `main` ([[ADR-0016-two-view-scoring-strict-gate]]).
- Option not tested: add 2024 (713k more games, about 2.2 epochs in 9 h). D says older games help, but 2024 is further from today's sets.

## Needs from the user
- The Mac must stay awake: lid open, or on power with an external display. Clamshell sleep on battery pauses runs ([[environment-quirks]]).
- A go-ahead for the tests (about 4.5 h), then a separate go-ahead for the overnight run once the tests are read.

## Related
- [[spec-eval-model]] · [[2026-11-22-main-run-results]] · [[ADR-0005-overnight-training-budget]] · [[ADR-0012-training-data-v1]]
