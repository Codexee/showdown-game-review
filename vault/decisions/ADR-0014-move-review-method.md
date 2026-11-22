---
title: ADR-0014 Move review method
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model, area/ui]
---

# ADR-0014: Grade each choice by regret over a simulated one-turn choice matrix

## Context
- Stage 6 needs labels such as "mistake" and a best choice for each turn ([[roadmap]]).
- The eval swing V(after) − V(before) mixes both players' choices and the dice, so it can't grade one player's choice by itself ([[benchmark-best-in-class]] P1 item 6).
- PS Dashboard grades choices with a depth-1 matrix of both sides' options, solved as a zero-sum game, with 5 / 10 / 20 point bands ([[2026-11-22-prior-art-research]]). Jaxcalibur and mikumiku37 search one ply over sampled worlds ([[2026-11-22-prior-art-jaxcalibur-mikumiku]]).
- Random-battle replays carry an inputlog, so the exact battle can be rebuilt at its commit ([[ADR-0009-randbats-full-info-reconstruction]]).

## Decision
1. **Candidates:** for each side, the top K choices (default 6) by our policy head, plus the choice actually played and the best Tera variant. Other choices are not graded.
2. **Transitions:** every candidate pair runs on Showdown's simulator from the exact turn-start state (rebuilt from the inputlog at its commit), with S seeds (default 16). If a Pokémon faints mid-turn, the replacing side gets the best replacement leaf.
3. **Leaf:** our value network on each player's **public view** after the turn, averaged over the two perspectives.
4. **Solve:** the pair matrix is solved as a zero-sum game with regret matching+ (averaged strategies).
5. **Regret:** best option's value minus the played option's value, both against the opponent's equilibrium mix. Bands: inaccuracy 5, mistake 10, blunder 20 points. One tier softer when the side was already at 85% or more. "No blame" when the Pokémon could not act (`|cant|`), "forced" when there was one option.
6. **Luck:** the value after the turn minus the expected value of the played pair over seeds.
7. **Accuracy:** Lichess's formula on each graded choice's regret, averaged per player.
8. **Scope:** Gen 9 Random Battle singles with an inputlog. Results are cached per game and tagged with the model; a new model marks them stale. Finished games only ([[ADR-0013-post-game-analysis-only]]).

## Known limits (flagged, not solved)
- **Hindsight in the transitions.** The simulator runs with the real hidden sets, so damage, speed and items follow what was actually on the field, not what the player could know. The leaf uses only public views. The benchmark plan was to sample hidden sets from the randbats priors ("worlds") instead; that is not built yet. Until then a choice can be graded against information the player did not have. **Unknown:** how often this changes a verdict; measure it when worlds are built ([[open-questions]] #6).
- Luck is per turn, not per chance event (no crit / miss / secondary ledger yet).
- No softening when the verdict depends on a hidden item.
- Depth 1 only: setup moves and long plans are valued only through the leaf.

## Consequences
- About 30 s per 25-turn game on this Mac; the review runs in a background job.
- Verdict quality is bounded by the value network; a better model changes the grades (stale results can be re-run).
- VGC needs a doubles engine path and a doubles model first ([[ADR-0002-format-order]]).

## Related
- [[spec-review-app]] · [[2026-11-22-stage6-results]] · [[module-map]] · [[benchmark-best-in-class]]
