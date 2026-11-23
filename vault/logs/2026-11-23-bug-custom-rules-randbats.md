---
title: "Bug: custom-rule tournament games pass as gen9randombattle"
type: log
tags: [area/data, area/model]
updated: 2026-11-23
---

# Bug: custom-rule tournament games pass as `gen9randombattle`

## Symptom
`training/search_eval.py` (perfect mode) stopped on `gen9randombattle-2717355576`: `review engine: TypeError: Cannot read properties of undefined (reading 'set')` at Showdown `dist/sim/state.js:117` (`State.deserializeBattle`), on turn 1.

## Cause
The game is a tournament battle with custom rules. Its inputlog format is `gen9randombattle@@@Mayhem,Picked Team Size = 6,Max Team Size = 24`, and its log lists Camomons, Inverse and Scalemons mods. Each player picks 6 of 24 Pokémon (`>p1 team 19, 16, 12, 18, 4, 24`). After the pick, the serialized side's team order still names slots 7–24, which the restored side doesn't have, so the lookup returns `undefined`. The replay's `formatid` is still `gen9randombattle`, so our filters let it through.

## Size
- Pinned bank: 35 of 3,709 games have `@@@` in the inputlog format (0.84% of positions); 17 show non-standard `|rule|` lines. `main@9000` scores well on them (two-view log-loss 0.4665 against 0.5838 on the rest), so they barely move the bank's score.
- 2026 training data (10,000-game sample of `data/hf`): 13 games (0.13%) with non-standard rules.
- 53 games in the pinned bank plus `data/train/inputlog` carry a team-pick choice.

## Fix (not done yet)
- The move review's `supported()` (`server/review/jobs.py`) and `training/build_dataset.py` should reject inputlogs whose format has `@@@` and logs with rules outside the standard four (Species Clause, HP Percentage Mod, Sleep Clause Mod, Illusion Level Mod). Until then, the move review fails on such games with this error.
- `search_eval.py` now records a failing game and goes on.

## Related
- [[plan-model-gains]] · [[ADR-0009-randbats-full-info-reconstruction]] · [[2026-11-22-bug-sim-snapshot-mutation]]
