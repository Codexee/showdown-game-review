---
title: v1.2 test runs and no-training eval gains, results
type: raw
source: local runs 2026-11-22 22:41 to 2026-11-23 03:00 EST (data/models/v12tests.log, data/models/*/test_test_pinned.json, gate_vs_*.json, data/models/search_eval/*.jsonl)
tags: [area/model]
created: 2026-11-23
---

# v1.2 tests and eval gains (2026-11-23)

All scores on the pinned bank (3,709 future games, 174,608 positions), both players' views averaged ([[ADR-0016-two-view-scoring-strict-gate]]), log-loss (lower is better), 90% bootstrap bands over games.

## Training tests (4 epochs, d=256, 6 layers, 6.97M params, bs 2048, lr 4e-4)
| Run | Data | Settings | Best val value loss (step, epoch) | Last val | Pinned log-loss | Accuracy |
|---|---|---|---|---|---|---|
| A `v12a` | medium (137,912 games since 2026-08-01) | dropout 0.1, wd 0.05 | 0.5707 (3,600, 2.33) | 0.5818 | 0.59736 | 66.69% |
| B `v12b` | medium | dropout 0.2, wd 0.1 | 0.5695 (5,600, 3.63) | 0.5718 | 0.59734 | 66.74% |
| C `v12c` | medium | B + value weight 1 → 0.2 after epoch 1 | 0.5682 (6,000, 3.89) | 0.5685 | 0.59551 | 66.87% |
| D `v12d` | mix25 (282,264 games: medium + 2025-07..09) | B | 0.5820 (7,200, 2.29)* | 0.5879* | 0.58941 | 67.31% |
| `main@9000` (installed) | full (672,326 games since 2026-01-01) | dropout 0.1, wd 0.05, 9 h | 0.5755 (9,000, 1.19) | | 0.58285 | 67.65% |

*D's validation split includes 2025 games, so its validation loss is not comparable with A–C.

Paired gates (b − a):
- A → B: −0.00002 [−0.00237, +0.00219], no clear difference.
- B → C: −0.00183 [−0.00333, −0.00027], C better.
- B → D: −0.00794 [−0.01137, −0.00443], D better.
- C → D: −0.00610 [−0.00935, −0.00295], D better.
- main → B / C / D: +0.01450 / +0.01266 / +0.00656, all worse (bands above zero).
- Single-view scoring had B ahead of A by 0.00165 [−0.00395, +0.00059]; under two views the difference is gone.
- Step time: medium about 0.47 s; mix25 0.65 s (135.8 min for 12,564 steps), with the search test below sharing the CPU from 00:50, so the cause of the slowdown is not separated.

## No-training ideas, on `main@9000`
- Ensembles of existing runs: all worse than `main` alone (`main`+C, mean of probabilities, +0.00272 [+0.00089, +0.00452]; logit weights 0.6–0.8 on `main` +0.0019 to +0.0004). A, B and C averaged score like C alone (0.59546).
- Temperature by rating band or phase: fitting on the bank itself gains at most 0.0033 in one band (1400–1600) and 0.0002 overall; one temperature fits.
- Bench-order symmetry: no test needed. The network has no slot positions (only own/opponent/field kind embeddings) and the value head averages tokens (`training/model.py`), so it is order-blind.
- Players' rating gap (from `|raw|` "rating before" lines, 2,708 games): median gap 30 points; the higher-rated player won 50.3%; adding the gap to the network's logit, cross-fitted by game halves, changes nothing (+0.00138, the same as refitting the logit alone).

## One-turn search as the eval (`training/search_eval.py`)
200 random pinned games (seed 0), the move review's solved matrix at each turn start (top 6 per side, 16 seeds per pair; worlds: 16 sampled worlds), p1's chance = mean of p1's best value and 1 − p2's best value. 1 game failed (custom rules, [[2026-11-23-bug-custom-rules-randbats]]); 199 games, 4,485 turns. Network on the same turns: 0.5851.
| Mode | Search alone | Blend 25% | Blend 50% | Blend 75% | Time per game (5 workers) |
|---|---|---|---|---|---|
| perfect (real hidden sets: hindsight) | −0.0087 [−0.0140, −0.0027] | −0.0045 | −0.0077 | −0.0098 [−0.0132, −0.0063] | 55 s |
| worlds (what each player could see) | −0.0047 [−0.0118, +0.0037] | −0.0038 | −0.0066 | −0.0083 [−0.0118, −0.0048] | 141 s |

Accuracy, worlds: network 65.7%, search 67.2%. The blend weights were picked on these same games (3 choices); 0.75 was best in both modes.

## Data hygiene
35 of 3,709 pinned games are custom-rule tournament games labelled `gen9randombattle` (0.84% of positions; `main` log-loss 0.4665 on them); 0.13% of a 10,000-game 2026 training sample ([[2026-11-23-bug-custom-rules-randbats]]).
