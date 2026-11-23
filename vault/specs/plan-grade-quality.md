---
title: "Plan: grade quality (verdict bank, fairness fix, depth-2 re-check)"
type: spec
status: active
tags: [area/model]
updated: 2026-11-23
---

# Plan: grade quality

The stage after model testing ([[ADR-0018-grade-quality-before-ui]]). Draft: it starts once the overnight run `v12` is read.

## Goal
Measure whether the move review's verdicts are right, then fix what the measure shows. Today we only know that verdicts are *sensitive* (worlds vs real sets changed 6% of flags; [[2026-11-22-worlds-vs-perfect-results]]), not which verdict is correct ([[2026-11-23-codex-review]] finding 7).

## Steps, in order
1. **Verdict bank** (the measure). About 60 graded choices from pinned-bank games, picked to cover:
   - turns where worlds and real-set grades disagree (the 36 flips from [[2026-11-22-worlds-vs-perfect-results]] are a start);
   - close calls within 1 point of a band;
   - setup and sacrifice turns; switches; Tera choices;
   - small endgames (≤3 Pokémon a side), where a deep exact search can serve as truth.
   For each choice the bank stores the game, turn, side, the choice, and a reference verdict. Reference sources, best first: (a) exact or deep search on small endgames; (b) the user's own judgment, shown blind (no model verdict); (c) a high-effort re-search (64+ seeds, all legal choices, depth 2). **Unknown:** how many the user wants to label; the bank works with (a) and (c) alone.
   Scores: agreement with the reference on "flagged vs not" and on the band; mean regret error; stability across independent seeds (Codex: the earlier noise check shared seeds).
2. **Fairness fix in worlds mode** ([[2026-11-23-codex-review]] finding 6). Today each world has one dice seed per choice pair and is solved on its own, so the graded player gets a different best answer in worlds they can't tell apart, and a lucky roll steers both answers.
   - Average several seeds inside each cell first (or price chance by outcome classes, as PS Dashboard does).
   - Solve one mixed strategy for the graded player across all worlds, with the opponent answering per world (it knows its own set).
   - Cost: more simulator calls per cell; measure against the 141 s per game now.
3. **Depth-2 re-check of flagged choices** ("can acquit, never convict"; [[goals-endgame]] goal 4). For each choice graded inaccuracy or worse, re-value the played choice and the best choice one turn deeper: after each cell's turn, solve the next turn's (smaller, top-K) matrix with the network at the leaf. The verdict may only improve. About 10% of choices are flagged, so the cost is bounded.
4. **Score again on the verdict bank** after each change, with a paired comparison against the previous version (same idea as the model gate, [[ADR-0016-two-view-scoring-strict-gate]]).
5. Smaller items, if the bank shows they matter:
   - audit every legal Tera and switch choice, not only the policy's top K (Codex finding 7);
   - full paralysis / sleep: keep "no blame" for the dice, but still grade "attack vs switch" when a switch was legal (Codex finding 7);
   - hidden-item sensitivity: soften a verdict that flips under a plausible hidden item ([[goals-endgame]] goal 6);
   - drop custom-rule games ([[2026-11-23-bug-custom-rules-randbats]]).

## Results so far
- **Step 1 built (2026-11-23):** `training/verdict_bank.py`, bank of 69 choices ([[2026-11-23-verdict-bank-v1]]). Default vs high-effort reference: 92.8% same flag, mean regret difference 0.61; default vs itself with new seeds: 89.9%, 0.48. Noise is the largest measured error; close calls flip about 1 in 5. References so far are high-effort re-searches only (source c); exact endgames (a) and blind labels (b) not yet.
- Next: step 2 (fairness fix), which averages several dice per cell and so should also cut this noise; re-score on the same bank.

## Done when
- The verdict bank exists and the move review's score on it is recorded.
- The fairness fix and the depth-2 re-check each pass a paired check on the bank (better, or no worse at lower cost).
- Time per game is recorded for each.

## Related
- [[ADR-0018-grade-quality-before-ui]] · [[goals-endgame]] · [[ADR-0014-move-review-method]] · [[ADR-0015-move-review-sampled-worlds]] · [[2026-11-23-codex-review]]
