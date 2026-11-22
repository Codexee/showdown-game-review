---
title: P0 A/B results (model v1.1 vs test2)
type: raw
date: 2026-11-22
source: training.train / test_model / compare_runs runs in session 15119347; files in data/models/p0, data/models/test2 (git-ignored)
---

# P0 A/B results (raw)

Do not edit. Synthesized into [[spec-eval-model]] and [[benchmark-best-in-class]]. The user chose "Yes, do P0 first" on 2026-11-22.

## Setup
- Same data (`medium`: 137,912 games, Aug–Oct 2026, rebuilt with the new columns) and the same 12-minute budget as `test2`.
- `p0`: d=256, 6 layers, **6.97M params** (test2: 4.27M); property tables, randbats priors, last-turn events, auxiliary heads, temperature. ≈340 steps/min (test2 ≈600).
- Pinned bank: 3,709 collected games (Nov 2026, after the training data), 174,608 samples, both sides. test2 scored with the stage-5 code (commit 687f885) in a scratch worktree; same sample keys.
- Rating distribution: training (medium) median 1676, p90 2138, 89% rated; pinned bank median 1427, p90 1998, 83% rated → part of the train→test gap is skill mix, not only set drift.

## Validation (same period)
| step | value loss | acc | T | policy top1/top3 | opponent's choice top1/top3 |
|---|---|---|---|---|---|
| 1000 | 0.5968 | 0.663 | 0.97 | 0.361/0.723 | 0.353/0.718 |
| 3000 | 0.5773 | 0.682 | 1.02 | 0.451/0.804 | 0.448/0.799 |
| 4096 | **0.5739** | 0.684 | 1.07 | 0.479/0.824 | 0.471/0.817 |
test2 best: 0.5746 at step 6000 (policy 0.474/0.822 at 7234). Placeholder: 0.6265 / 0.645.

## Pinned future games (calibrated, T = 1.074 from validation)
- **Model:** log-loss 0.6026 (90% CI 0.5926–0.6133), Brier 0.2085, acc 66.2% (65.4–66.9%), ECE 0.027.
- **Placeholder:** 0.6375, Brier 0.2235, acc 62.9%. Model − placeholder log-loss 90% CI [−0.042, −0.028].
- By phase (acc model / placeholder): early 0–2 fainted 61.0 / 57.3; mid 3–6 70.0 / 67.3; late 7+ 72.8 / 69.8.
- Rating 1500+ (58,236 samples, 1,100 games): model 0.6208 / 64.3%; placeholder 0.6490 / 61.2%.
- Policy top1/top3 0.478 / 0.821; opponent's choice top3 0.817.
- **Set prediction, only on what wasn't revealed yet at that turn:** item 0.89, ability 0.945, Tera 0.658, unrevealed moves in top-4 0.83. (Counting revealed ones too gave 0.95 / 0.99 / 0.77 / 0.96 — inflated; fixed in `collect`.)

## Paired gate p0 vs test2 (`compare_runs`, 1,000 bootstrap resamples over games)
| slice | log-loss test2 | log-loss p0 | Δ (p0 − test2) | 90% band |
|---|---|---|---|---|
| overall | 0.6136 | 0.6026 | −0.0110 | [−0.0181, −0.0042] |
| early | 0.6571 | 0.6523 | −0.0048 | [−0.0104, +0.0003] |
| mid | 0.5714 | 0.5653 | −0.0061 | [−0.0138, +0.0013] |
| late | 0.5801 | 0.5404 | −0.0397 | [−0.0731, −0.0129] |
| rating 1500+ | 0.6404 | 0.6208 | −0.0196 | [−0.0375, −0.0059] |
Brier overall −0.0024 [−0.0044, −0.0005]. Accuracy 65.9% → 66.2%. **Verdict: p0 better.**
- Raw vs raw (no temperature on either): Δ −0.0082 [−0.0155, −0.0015] → the gain is mostly from features/heads, calibration adds ≈−0.003.
- Installed p0 as `data/models/current.pt`; review screen text: "66% … on newer games it never saw (placeholder: 63%)".
