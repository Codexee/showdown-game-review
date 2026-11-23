---
title: Benchmark against best-in-class tools
type: wiki
status: active
tags: [area/model, area/ui, area/data]
updated: 2026-11-22
---

# Benchmark: how we compare, and what to change

Sources: [[2026-11-22-prior-art-research]], [[2026-11-22-prior-art-jaxcalibur-mikumiku]]. The closest analogue and the bar to beat for the *review tool* is **PS Dashboard** (a "chess engine for Showdown replays"). The strongest *models* are **Jaxcalibur** (Gen 9 Random Battle: #1 on the ladder, peak 2557 Elo / 95.3 GXE, 8.5M params, self-play) and **mikumiku37** (Champions VGC Reg M-C: #1, 1857 Elo / 81.2 GXE, 8.7M params, self-play). Both keep code and weights private.

## What the two #1 bots tell us
- **Self-play beats human data at the top.** Both trained only by self-play (Jaxcalibur ~100M games in a week on one H100; mikumiku ~330M games in 48 h on one RTX 5090). Our human-data model is the right v1 for a review tool (it learns how real games go), but the strongest value function needs self-play later. That needs a **fast engine**: both built their own (JAX on GPU; Rust ≈650× Showdown). For us the realistic option is **poke-engine** (Rust, already a dependency through foul-play; unverified speed for self-play).
- **Small networks:** ~8.5M parameters, trained longer, beat larger ones (Jaxcalibur). Our overnight plan used 12.6M; drop to ≈6–8M.
- **Static dex data as inputs** (both): types, base stats, move data. Confirms P0 item 1.
- **Auxiliary heads** (Jaxcalibur): predict each opposing Pokémon's item, ability, moves and Tera type, and the **opponent's next action**; the latter "made the bot substantially stronger". We have labels for both: the opponent's next action from every log, and hidden sets exactly from the inputlog rebuild (ADR-0009) or partly from what gets revealed later in the same game.
- **History and matchup tokens** (Jaxcalibur): last 16 events; damage calcs per Pokémon pair, added halfway through.
- **Search = one ply over sampled worlds, solved as a matrix game** (mikumiku: 16 worlds, top-8 × top-8, several RNG seeds per cell, regret matching; Jaxcalibur: pUCT over 32 worlds). This is exactly our planned move-review method (P1 item 6), with our value net at the leaf and hidden sets sampled from randbats priors / the set-prediction head. Use 64–128 seeds per cell for stable grades (mikumiku: 4 seeds gave nonsense). Search adds ~100–150 Elo; most of the strength is the network.
  > [!warning] Conflict
  > "One ply" fits mikumiku only. Jaxcalibur searches depth 4, about two turns, sharing nodes by revealed state ([[2026-11-22-prior-art-jaxcalibur-mikumiku]], [[2026-11-23-codex-review]] finding 6). [[ADR-0014-move-review-method]] Context groups both as "one ply". The ADR body is read-only; the decision itself doesn't depend on this.
- **Doubles policy:** each slot's action includes its target; slot 2 conditioned on slot 1 (pairwise term) with pair legality masks (mikumiku). For stage 7.
- **Fair play:** both withheld their bots over ladder and tournament cheating. Our tool must only analyze **finished** games ([[ADR-0013-post-game-analysis-only]]).

## Where we already stand out
| | Us | Best known |
|---|---|---|
| Ground truth for the log parser | Graded against Showdown's simulator: 99.4% of turn states exact on unseen games, 100% after fixes ([[battle-parser]]) | PS Dashboard corrects HP/status at turn boundaries; no published parser accuracy |
| Hidden info in randbats training data | **Exact** full-information rebuild from inputlogs at the logged commit, 61/61 then 1,283/1,283 ([[ADR-0009-randbats-full-info-reconstruction]]) | Others guess sets from usage stats; PS Dashboard rebuilds dice but guesses sets |
| Value function data | Learned from 100k–650k real games | PS Dashboard: hand-built terms with weights fitted on ~5,600 games |
| Your own games | Automatic archive of every game (poller + userscript), offline review | PS Dashboard and the extensions work one replay at a time, online |
| Honest numbers | Placeholder baseline in every evaluation; future-games test set | PS Dashboard: paired bootstrap gate (stronger than ours, see below) |

## Gaps, ranked

### P0: before the overnight run (they change the model's inputs or how it's judged) — **done 2026-11-22** ([[2026-11-22-p0-ab-results]]: passes the paired gate)
1. **Properties, not just ids** (ps-ppo): base stats and types for each Pokémon; base power, accuracy, type, category, priority for each move. Helps with rare species and with **drift** (the value edge fell from +4.1 to +2.2 accuracy points on newer games, [[2026-11-22-training-test-runs]]).
2. **Randbats set priors for unrevealed information:** for each opponent Pokémon, the distribution of possible moves, items, abilities and Tera types from pkmn's randbats stats ([[data-sources]]), as a weighted bag. Randbats sets come from fixed pools, so this is information the player really has, and the others don't use it this way.
3. **Recent events as input** (ps-ppo: last turn; Jaxcalibur: last 16 events as tokens): who moved first (speed information), moves used, crits, misses, super-effective hits.
3b. **Auxiliary heads** (Jaxcalibur): opponent's next action (labels in every log) and opponent's hidden set (exact labels from the inputlog rebuild; partial labels from later reveals in the same game).
3c. **Smaller model, trained longer** (Jaxcalibur, mikumiku: ~8.5M): change the overnight default from 12.6M to ≈6–8M.
4. **Measurement like PS Dashboard:** bootstrap confidence intervals over games; calibration and Brier **by game phase**; a **high-rating slice** (the dataset has ratings for 72% of games); a **paired comparison** of old vs new model on the same pinned test games before switching the installed model.
5. **Post-hoc calibration** (temperature or per-phase scaling) fitted on validation, checked on the future-games test set.

### P1: stage 6, move review (this is where PS Dashboard is far ahead)
*Status 2026-11-22: items 6 (over sampled worlds, [[ADR-0015-move-review-sampled-worlds]]; unseen species still real), 7 (except hidden-item softening) and 9 built; 8 is per turn only ([[ADR-0014-move-review-method]]).*
6. **Grade choices by regret in win probability, not just by the swing.** The swing V(next) − V(now) mixes both players' choices and luck. Best practice: value every option, then regret = value(best) − value(played). Plan: on the simulator, with hidden sets sampled from the randbats priors, evaluate every pair of choices one turn deep with **our learned value as the leaf**, and solve the matrix as a zero-sum game (PS Dashboard's depth-1 approach, with a learned leaf instead of hand-built weights).
7. **Verdict bands:** PS Dashboard uses inaccuracy 5 / mistake 10 / blunder 20 points of regret; Lichess uses 10 / 20 / 30 points of win-chance drop. Start with 5 / 10 / 20 (Pokémon turns are coarser and swingier than chess moves, so small regrets matter), soften once a side is at ≥85%, no blame for full paralysis / sleep / flinch, and soften when the verdict depends on a hidden item.
8. **Decision vs luck split** and a **luck ledger** (Hindsight, Luck Analyzer): every provable chance event (crits, misses, secondaries, full para), weighted by improbability × swing; accuracy credited both ways.
9. **Accuracy score per player** (Lichess-style, from win-probability losses) and **lead grading** (turn 0).
10. **Provenance labels** in the UI: revealed / guessed (from priors) / your team paste.

### P2: reach
11. **PS Dashboard engine protocol** (`ps-dashboard-engine/1`, JSON over HTTP): expose our model as an engine, so it works inside PS Dashboard too. Cheap, and puts our value function next to theirs.
12. **Play your own line** (variations from any turn): needs the simulator behind the review screen.
13. **Endgame exactness:** a small solver for ≤2–3 Pokémon a side, to grade the model where truth is computable.
14. **Self-play fine-tuning** (Jaxcalibur, mikumiku, ps-ppo, Metamon) to go beyond human play; needs a fast engine (poke-engine first); **distributional value head**. **Matchup tokens** with damage calcs (Jaxcalibur).
15. **VGC Reg M-C:** read PokaiTrainer (belief-state equilibrium search, 2026) and VGC-Bench before building.

### Engineering practices worth copying
- A pinned evaluation bank and a paired gate before adopting a model change (P0 item 4).
- Playwright end-to-end checks of the review screen (we check by hand in the browser today).
- Keep the parser's simulator-graded test as the guard for every parser change (already in place).

> [!warning] Conflict
> [[ADR-0014-move-review-method]] Context describes PS Dashboard as grading with "a depth-1 matrix". Our own raw note lists depth 1, depth 2 and MCTS (DUCT), plus re-searching every flagged mistake one depth deeper ([[2026-11-22-prior-art-research]]). The user raised this as the project's main gap on 2026-11-23 ([[2026-11-23-endgame-goals-and-overnight-go]], [[goals-endgame]]). The ADR body is read-only.

## Second opinion: Codex review (2026-11-23)
Source: [[2026-11-23-codex-review]] (verbatim, with Claude's checks). Web claims there are unverified until read.
- **Confirmed:** the overnight script can install a model with no passing gate (`RUN` defaults to the installed run's name, and an unclear gate exports). Must be fixed before the overnight run.
- **Confirmed, measured:** averaging p1's view and 1 − p2's view (as the move review already does) improves `main` on the pinned bank: log-loss 0.58543 → 0.58285 (band −0.0027 to −0.0025), accuracy 67.4% → 67.6%. The eval bar and the gate use one view today.
- **Open diagnosis:** the "one label per game" cause of value overfitting is a hypothesis. A game-balanced value-sampling test would check it (no bot writeup confirms this practice; unverified).
- **Move review, later:** each world is solved separately with one dice seed per cell, so the graded player gets a different best answer in worlds they can't tell apart, and a lucky roll can steer both answers. Fix: average dice inside each cell first, then one strategy for the graded player across worlds. Also sample the unseen bench (Eevenator, Foul Play), audit every Tera and switch choice, and build a small bank of checked verdicts.
- **New references (unverified):** Nessie (1.5M params, ~375k search-guided games, damage/survival aux heads), Mew's Truck (scores 90 bring-4/lead-2 plans), Ninjask (open Champions VGC simulator), Eevenator, MissingNo.Zero, Numbrion, Metamon TD backups, PokaiTrainer.

## Decision needed
Which of P0 to do before the overnight run: [[open-questions]].

## Related
- [[spec-eval-model]] · [[spec-review-app]] · [[roadmap]] · [[2026-11-22-prior-art-research]]
