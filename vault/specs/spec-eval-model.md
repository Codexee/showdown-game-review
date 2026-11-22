---
title: Spec: eval model and training
type: spec
status: active
tags: [area/model]
updated: 2026-11-22
---

# Spec: eval model and training

> [!note] Status 2026-11-22
> Pipeline built and tested; a small model (`test2`) is installed and drives the eval bar for singles. On games played after its training data it calls the winner **66% vs 64%** for the remaining-HP placeholder ([[2026-11-22-training-test-runs]]). The overnight run (`./training/overnight.sh`) has not been run yet.

## Goal
For any turn of a game, output (a) the win chance for each side, which drives the eval bar, and (b) a ranking of the choices, for move review. First format: Gen 9 Random Battle; then VGC 2026 Reg M-C ([[ADR-0002-format-order]]).

## v1 (built): data and inputs ([[ADR-0012-training-data-v1]])
- **Training data:** public `gen9randombattle` logs from the HolidayOugi Hugging Face dataset (2.0M games to 2026-10-05), recent months only, main server only.
- **Test data:** games collected from Showdown's API for the 14 days before 2026-11-22 (after the dataset ends), with inputlogs; also rebuilt to full information ([[ADR-0009-randbats-full-info-reconstruction]]).
- **Input:** the public view at each turn start from one player's side: 13 tokens (6 own, 6 opponent, field). Per Pokémon: species, item, ability, 4 revealed moves, Tera (ids; unknown = UNK, known-empty = NONE) and HP, fainted, active, seen, level, statuses, boosts, key volatiles. Field: turn, weather, terrain, Trick Room etc., hazards and screens per side, Tera used, and per-side totals (HP left, Pokémon alive, Pokémon unseen).
- **Targets:** value = this player won. Policy = the move id or own switch slot chosen at the turn start (pivot switches, post-faint switches, called moves and `|cant|` turns excluded).

## v1 model (`training/model.py`)
Transformer encoder over the 13 tokens, no positions within a side (only own / opponent / field embeddings). Value head on [field token, mean of tokens]. Policy head: move logits from the active Pokémon's token, switch logits per own token, with a mask (no fainted / active; only the first unseen slot). Loss = BCE(value) + 0.5 · CE(policy).

## Training (`training/train.py`)
AdamW, warmup then cosine, gradient clipping. Saves `last.pt` (resume), `best.pt` (best value loss: what the eval bar uses), `best_policy.pt`, `metrics.jsonl`. Every evaluation also reports the placeholder's score on the same samples, so "beats the baseline" is checked, not assumed. Time budget and SIGTERM/Ctrl-C stop cleanly.

## Overnight run (`training/overnight.sh`, [[ADR-0005-overnight-training-budget]])
Builds the full dataset (games since 2026-01-01, ≈650k games / ≈15–16M samples), trains d=384, 6 layers (12.6M params, ≈4.5k samples/s, ≈1 h per epoch) for 9 h with `caffeinate`, scores on future games, then installs the model (`training/export.py` → `data/models/current.pt`). Resumable.

## Evaluation
- Value: log-loss, accuracy, Brier, calibration error (ECE), accuracy by turn range; always next to the placeholder.
- Policy: top-1 / top-3 agreement with the human choice.
- Main number: **future games**, not same-period validation (validation overstated the value edge in test2).

## Known gaps / next
- **Drift:** the value head's edge shrinks on newer games. Options: train on more recent games (keep collecting), add the collected inputlog games to training.
- **v2:** use the full-information rebuild (ADR-0009) for an auxiliary head that predicts the opponent's hidden sets; Tera decision; doubles (VGC Reg M-C) model.
- Self-play stage and play strength vs foul-play: not started.

## Related
- [[bot-landscape]] · [[formats]] · [[data-sources]] · [[environment]] · [[spec-review-app]] · [[battle-parser]]
