---
title: ADR-0017 Eval bar blends the move review's search
type: adr
status: accepted
date: 2026-11-23
supersedes:
superseded_by:
tags: [area/model, area/ui]
---

# ADR-0017: After a move review, the eval bar shows 75% search + 25% network

## Context
- The move review solves a one-turn choice matrix every turn ([[ADR-0014-move-review-method]], [[ADR-0015-move-review-sampled-worlds]]). Its value, each side's best choice against the other's equilibrium answer, is a one-turn search over our network.
- On 199 future games, blending it 75/25 with the network beat the network alone by 0.0083 log-loss [−0.0118, −0.0048] in worlds mode (what each player could see), and by 0.0098 with the real hidden sets ([[2026-11-23-v12-tests-and-eval-gains-results]]). That is about 3× the two-view gain ([[ADR-0016-two-view-scoring-strict-gate]]) and larger than any training change tested.
- Jaxcalibur: search adds ≈100–150 Elo on top of the network ([[2026-11-22-prior-art-jaxcalibur-mikumiku]]).
- The user chose to build this before the overnight run ([[2026-11-23-search-bar-first]]).

## Decision
1. When a game has a finished move review that is current (same model, same analysis version) and in **worlds** mode, `GET /api/games/{id}/review` sets each turn's `eval` to `0.75 × search + 0.25 × network`, keeps both parts (`eval_search`, `eval_model`), and reports `eval_method: "model+search"` with an explanation.
2. p1's searched chance = mean of p1's best value and 1 − p2's best value (`server/review/analyze.py` `search_value_p1`, shared with `training/search_eval.py`).
3. Perfect-mode reviews are **not** used for the bar: they use the real hidden sets.
4. Turns without a search value (no choice to grade) and the end step keep the network or the exact result.
5. The review screen fetches the blended eval once when a current review is loaded or finishes.

## Consequences
- The bar improves only for analysed games (about 1–2.5 minutes each). Unanalysed games keep the network.
- The weight 0.75 was chosen on the same 199 games (3 choices tried). A fresh 100-game check (games 200–299 of the same shuffle) is running; **Unknown:** whether 0.75 holds there. If it doesn't, change `SEARCH_BLEND`.
- A new model or analysis version makes the review stale, which returns the bar to the network until it is re-run.
- Later: distil search values into the network so every game gets the gain ([[plan-model-gains]] next step 3).

## Related
- [[plan-model-gains]] · [[spec-review-app]] · [[ADR-0016-two-view-scoring-strict-gate]] · [[module-map]]
