---
title: Spec: eval model and training
type: spec
status: draft
tags: [area/model]
updated: 2026-11-22
---

# Spec: eval model and training (draft)

## Goal
For any turn of a game, output (a) the win chance for each side, which drives the eval bar, and (b) a ranking of the legal choices, for move review. First format: Gen 9 Random Battle; then VGC 2026 Reg M-C ([[ADR-0002-format-order]]).

## Method (following [[bot-landscape]])
1. **Parse replays into per-side views.** Turn each archived log into the battle state as each player saw it: revealed moves, items, abilities, HP, status, boosts, field. This is the same step Metamon uses.
2. **Set priors.** For randbats, use the random-set pool for each species. For VGC M-C, use Smogon usage and moveset stats, keeping species and moves at ≥1.5% usage if that rule still applies ([[open-questions]] #2).
3. **Model.** A transformer over the Pokémon and field tokens, with a value head (win chance) and a policy head (choice ranking). Size so one run fits [[ADR-0005-overnight-training-budget]].
4. **Training.**
   - Stage A: supervised. Policy learns the human's choices; value learns the final result (win/loss) from each turn.
   - Stage B: self-play against foul-play and earlier checkpoints on a local Showdown server via poke-env, to fix the value estimates.
5. **Test run first**, then one overnight run in the background with checkpoints and resume.

## Data
- Public replays of the target format (scraped into the archive by [[spec-replay-sync]]; the same code with `format=` instead of `user=`).
- **Unknown:** how many Gen 9 Random Battle replays can be collected in a few days. Measure before the full run.

## Evaluation
- Value: log-loss and calibration of win chance on held-out games.
- Policy: top-1 / top-3 agreement with human choices on held-out games.
- Play strength: win rate against the random AI, `SimpleHeuristicsPlayer` and foul-play on the local server.

## Related
- [[bot-landscape]] · [[formats]] · [[data-sources]] · [[environment]] · [[spec-review-app]]
