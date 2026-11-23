---
title: Endgame goals (beat PS Dashboard)
type: spec
status: active
tags: [area/model, area/ui]
updated: 2026-11-23
---

# Endgame goals

The user set these on 2026-11-23 ([[2026-11-23-endgame-goals-and-overnight-go]]). They are long-range goals, not the current stage (model testing, [[roadmap]]). Most match features PS Dashboard already has ([[2026-11-22-prior-art-research]]); the aim is to match them and then beat PS Dashboard.

## The headline goal: deeper search at the same speed
- **Now:** one-turn search only (a solved choice matrix per turn; [[ADR-0014-move-review-method]], [[ADR-0015-move-review-sampled-worlds]]). About 55 s per game with real sets and 141 s with 16 sampled worlds, 5 workers ([[2026-11-23-v12-tests-and-eval-gains-results]]).
- **PS Dashboard:** search on the real simulator over every legal choice pair, regret matching; **depth 1, depth 2 and MCTS (DUCT)**; chance priced by outcome classes from `@smogon/calc` instead of many random seeds ([[2026-11-22-prior-art-research]]).
- **Goal:** an engine that searches depth 2 and MCTS, better than PS Dashboard's, at the same speed. Measured on the same replays: verdict agreement on a checked verdict bank, winner-prediction log-loss (our paired gate), and time per game.
- **Ways to get the speed (to measure before choosing):**
  1. Profile first: how the 141 s splits between the Node simulator, the network and Python glue. **Unknown** until measured.
  2. Price chance by outcome classes (hit / miss / KO / secondary) instead of 16 random seeds per cell (PS Dashboard). Fewer simulator calls per cell.
  3. Use the policy head to prune: top-K per side already; at depth 2, expand only the likely lines (MCTS / DUCT with policy priors, as Jaxcalibur's pUCT does, [[2026-11-22-prior-art-jaxcalibur-mikumiku]]).
  4. Batch network calls across cells and worlds.
  5. A faster simulator: poke-engine (Rust, used by Foul Play), @pkmn/engine (Zig; Gen 9 support **unverified**), or our own like mikumiku37 (Rust, ≈650× Showdown) and Jaxcalibur (JAX). Exactness against Showdown at the replay's commit must be checked ([[ADR-0009-randbats-full-info-reconstruction]]).
- **Comparison target:** PS Dashboard is MIT and exposes an engine protocol (`ps-dashboard-engine/1` over HTTP) for outside engines ([[2026-11-22-prior-art-research]]). Running it locally on our bank would give a direct comparison. **Unknown:** whether it runs offline on this Mac.

## Goal list
| # | Goal | PS Dashboard has it | Our status | Stage |
|---|---|---|---|---|
| 1 | Hidden-set guessing from **usage stats + Smogon sets** | yes | Random Battle: sets from randbats role data (`server/review/worlds.py`). VGC: not built; usage stats are the source there ([[2026-11-22-direction-codex-review]]) | VGC |
| 2 | **EV spreads fitted to observed damage** | yes | not built (randbats sets have fixed EVs; matters for VGC) | VGC |
| 3 | **Choice Scarf inferred from move order** | yes | not built; worlds sample items from role rates only | move review |
| 4 | **Re-search every flagged mistake one turn deeper:** can acquit, never convict | yes | not built | move review (first step toward depth 2) |
| 5 | **Exact endgame solver**, ≤3 Pokémon a side | yes (also used as truth to grade estimators) | not built | move review |
| 6 | **Soften a verdict when a hidden item would flip it** (sensitivity probe) | yes | not built (listed in ADR-0014 known limits) | move review |
| 7 | **Self-play tuning**, after everything else | no | not built; needs a fast engine ([[benchmark-best-in-class]]) | last |
| 8 | **(VGC) a fast simulator**, as mikumiku37 built | no | not built; check Mew's Truck and Ninjask first ([[2026-11-23-codex-review]] finding 8) | VGC |

Also from the Codex review and our own tests, feeding these goals:
- Fairness fix in worlds mode: average the dice inside each cell, then one strategy for the graded player across worlds ([[2026-11-23-codex-review]] finding 6). Needed before depth 2, or depth 2 inherits the bias.
- A verdict bank to measure grade quality directly (Codex finding 7).
- Distil search values into the network ([[plan-model-gains]]).

## Related
- [[roadmap]] · [[benchmark-best-in-class]] · [[plan-model-gains]] · [[2026-11-23-codex-review]] · [[open-questions]]
