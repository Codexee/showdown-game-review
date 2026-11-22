---
title: Main training run results (model v1.1, full 2026 data)
type: raw
date: 2026-11-22
source: data/models/main.log, data/models/main/test_test_pinned.json, gate_vs_p0_test_pinned.json (git-ignored)
---

# Main run results (raw)

Do not edit. Synthesized into [[spec-eval-model]].

## Run
- `./training/overnight.sh`, started 2026-11-22 09:06 EST, detached; High Power mode, AC.
- Dataset `full`: games since 2026-01-01 → **672,326 games (925 skipped), 15,775,600 samples, built in 165 s on 15 cores.** Train 15,459,651 / val 315,949.
- Model v1.1, d=256, 6 layers, **6.97M params**, bs 2048, lr 4e-4, 7,548 steps/epoch, ≈1 h/epoch on MPS.
- **Stopped early by the user's go-ahead at 11:58** (step 20,319, epoch 2.69, 169 min) because the value head was overfitting; best value checkpoint was step 9,000.

## Validation (placeholder: 0.6315 / 63.8%)
| step | epoch | value loss | acc | T | policy top1/top3 | opp top1/top3 |
|---|---|---|---|---|---|---|
| 3000 | 0.40 | 0.5932 | 0.665 | 0.99 | 0.452/0.800 | 0.439/0.793 |
| 6000 | 0.80 | 0.5806 | 0.677 | 1.01 | 0.504/0.843 | 0.493/0.838 |
| **9000** | 1.19 | **0.5755** | 0.680 | 0.97 | 0.520/0.856 | 0.514/0.852 |
| 12000 | 1.59 | 0.5774 | 0.682 | 1.03 | 0.531/0.863 | 0.526/0.861 |
| 15000 | 1.99 | 0.5845 | 0.681 | 1.16 | 0.538/0.868 | 0.531/0.865 |
| 18000 | 2.39 | 0.6019 | 0.677 | 1.43 | 0.541/0.872 | 0.538/0.869 |
| 20319 | 2.69 | 0.6172 | 0.676 | 1.65 | 0.544/0.874 | 0.540/0.870 |
Value overfits after ≈1.2 epochs (every turn of a game shares one label); policy keeps improving slowly. `best.pt` = step 9000 (value); `best_policy.pt` = step 20319.

## Pinned future games (best.pt, T = 0.971)
- Model acc **67.4%**; placeholder 62.9%. By phase (model / placeholder acc): early 62.0 / 57.3; mid 71.1 / 67.3; late 75.0 / 69.8. Rating 1500+: log-loss 0.6030 / acc 65.6% vs placeholder 0.6490 / 61.2%.
- Policy top1/top3 (step-9000 weights) 0.524 / 0.860; opponent's choice top3 0.857.
- Set prediction on not-yet-revealed info: item 0.903, ability 0.953, Tera 0.678, unrevealed moves in top-4 0.848.

## Paired gate main vs p0 (3,709 games)
| slice | p0 | main | Δ | 90% band |
|---|---|---|---|---|
| overall | 0.6026 | **0.5854** | −0.0171 | [−0.0214, −0.0130] |
| early | 0.6523 | 0.6423 | −0.0100 | [−0.0142, −0.0063] |
| mid | 0.5653 | 0.5499 | −0.0154 | [−0.0213, −0.0100] |
| late | 0.5404 | 0.4990 | −0.0414 | [−0.0564, −0.0271] |
| rating 1500+ | 0.6208 | 0.6030 | −0.0178 | [−0.0251, −0.0098] |
Accuracy 66.2% → 67.4%. Verdict: better in every slice → **installed** as data/models/current.pt (step 9000).
