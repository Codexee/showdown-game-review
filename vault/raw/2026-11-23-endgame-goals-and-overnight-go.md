---
title: Endgame goals, search-depth concern, overnight go-ahead
type: raw
source: user message in chat, 2026-11-23 (about 03:50 EST)
tags: [area/model, area/ui]
created: 2026-11-23
---

# User message (2026-11-23, about 03:50 EST)

Paraphrased closely.

## Add to a list of endgame goals
1. Hidden-set guessing from **usage stats + Smogon sets**.
2. **EV spreads fitted to observed damage.**
3. **Choice Scarf inferred from move order.**
4. **Every flagged mistake re-searched one turn deeper**: "can acquit a move, never convict it".
5. **Exact endgame solver** at ≤3 Pokémon a side.
6. **Soften a verdict when a hidden item would flip it.**
7. **Self-play tuning**, after everything else is done.
8. **(VGC) Optimise the Showdown engine** the way mikumiku37 did (a fast simulator).

## Main concern
"The main issue I have with the project at the moment is the limitation to 1-turn search, whereas PS Dashboard does 2-turn and MCTS. The ideal outcome is that we have a better engine than PS Dashboard that is able to sim those at the same speed."

## Overnight run
"Start the overnight run now." (Answer to "Start the overnight run now, alongside the fresh check?")

## Pasted text in the same message
The user also pasted advice text, author not stated. In short: stop spending attention on more training tests after the overnight run; the bigger opportunities are (1) grade quality measured directly (a verdict bank, plus Codex's fairness fix), (2) a depth-2 re-check of flagged turns that can acquit but never convict, (3) the UI stage with VGC team import; "If you agree, I'll record that change of emphasis in the vault." The user's own words did not say whether they adopt it; Claude asked.
