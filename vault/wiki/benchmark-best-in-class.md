---
title: Benchmark against best-in-class tools
type: wiki
status: active
tags: [area/model, area/ui, area/data]
updated: 2026-11-22
---

# Benchmark: how we compare, and what to change

Sources: [[2026-11-22-prior-art-research]]. The closest analogue and the bar to beat is **PS Dashboard** (a "chess engine for Showdown replays"). The best neural Gen 9 Random Battle model on record is **ps-ppo** (1900+ ladder Elo from self-play).

## Where we already stand out
| | Us | Best known |
|---|---|---|
| Ground truth for the log parser | Graded against Showdown's simulator: 99.4% of turn states exact on unseen games, 100% after fixes ([[battle-parser]]) | PS Dashboard corrects HP/status at turn boundaries; no published parser accuracy |
| Hidden info in randbats training data | **Exact** full-information rebuild from inputlogs at the logged commit, 61/61 then 1,283/1,283 ([[ADR-0009-randbats-full-info-reconstruction]]) | Others guess sets from usage stats; PS Dashboard rebuilds dice but guesses sets |
| Value function data | Learned from 100k–650k real games | PS Dashboard: hand-built terms with weights fitted on ~5,600 games |
| Your own games | Automatic archive of every game (poller + userscript), offline review | PS Dashboard and the extensions work one replay at a time, online |
| Honest numbers | Placeholder baseline in every evaluation; future-games test set | PS Dashboard: paired bootstrap gate (stronger than ours, see below) |

## Gaps, ranked

### P0: before the overnight run (they change the model's inputs or how it's judged)
1. **Properties, not just ids** (ps-ppo): base stats and types for each Pokémon; base power, accuracy, type, category, priority for each move. Helps with rare species and with **drift** (the value edge fell from +4.1 to +2.2 accuracy points on newer games, [[2026-11-22-training-test-runs]]).
2. **Randbats set priors for unrevealed information:** for each opponent Pokémon, the distribution of possible moves, items, abilities and Tera types from pkmn's randbats stats ([[data-sources]]), as a weighted bag. Randbats sets come from fixed pools, so this is information the player really has, and the others don't use it this way.
3. **Last turn's events as input** (ps-ppo): who moved first (speed information), crits, misses, super-effective hits.
4. **Measurement like PS Dashboard:** bootstrap confidence intervals over games; calibration and Brier **by game phase**; a **high-rating slice** (the dataset has ratings for 72% of games); a **paired comparison** of old vs new model on the same pinned test games before switching the installed model.
5. **Post-hoc calibration** (temperature or per-phase scaling) fitted on validation, checked on the future-games test set.

### P1: stage 6, move review (this is where PS Dashboard is far ahead)
6. **Grade choices by regret in win probability, not just by the swing.** The swing V(next) − V(now) mixes both players' choices and luck. Best practice: value every option, then regret = value(best) − value(played). Plan: on the simulator, with hidden sets sampled from the randbats priors, evaluate every pair of choices one turn deep with **our learned value as the leaf**, and solve the matrix as a zero-sum game (PS Dashboard's depth-1 approach, with a learned leaf instead of hand-built weights).
7. **Verdict bands:** PS Dashboard uses inaccuracy 5 / mistake 10 / blunder 20 points of regret; Lichess uses 10 / 20 / 30 points of win-chance drop. Start with 5 / 10 / 20 (Pokémon turns are coarser and swingier than chess moves, so small regrets matter), soften once a side is at ≥85%, no blame for full paralysis / sleep / flinch, and soften when the verdict depends on a hidden item.
8. **Decision vs luck split** and a **luck ledger** (Hindsight, Luck Analyzer): every provable chance event (crits, misses, secondaries, full para), weighted by improbability × swing; accuracy credited both ways.
9. **Accuracy score per player** (Lichess-style, from win-probability losses) and **lead grading** (turn 0).
10. **Provenance labels** in the UI: revealed / guessed (from priors) / your team paste.

### P2: reach
11. **PS Dashboard engine protocol** (`ps-dashboard-engine/1`, JSON over HTTP): expose our model as an engine, so it works inside PS Dashboard too. Cheap, and puts our value function next to theirs.
12. **Play your own line** (variations from any turn): needs the simulator behind the review screen.
13. **Endgame exactness:** a small solver for ≤2–3 Pokémon a side, to grade the model where truth is computable.
14. **Self-play fine-tuning** (ps-ppo, Metamon) to go beyond human play; **distributional value head**.
15. **VGC Reg M-C:** read PokaiTrainer (belief-state equilibrium search, 2026) and VGC-Bench before building.

### Engineering practices worth copying
- A pinned evaluation bank and a paired gate before adopting a model change (P0 item 4).
- Playwright end-to-end checks of the review screen (we check by hand in the browser today).
- Keep the parser's simulator-graded test as the guard for every parser change (already in place).

## Decision needed
Which of P0 to do before the overnight run: [[open-questions]].

## Related
- [[spec-eval-model]] · [[spec-review-app]] · [[roadmap]] · [[2026-11-22-prior-art-research]]
