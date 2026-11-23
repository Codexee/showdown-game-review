---
title: Spec: eval model and training
type: spec
status: active
tags: [area/model]
updated: 2026-11-22
---

# Spec: eval model and training

> **Installed (2026-11-23): `v12@36000`** — games since 2025-01-01, dropout 0.2, wd 0.1, value-weight schedule; on 3,709 future games it calls the winner **68.2%** of the time (log-loss 0.574, both views), beating `main@9000` (67.6%, 0.583) in the paired gate ([[2026-11-23-v12-results]]). The published release is still `main@9000` ([[ADR-0021-publish-model]]).

> [!note] Status 2026-11-22
> **Installed: `main` (v1.1 on all 2026 games, 672k games):** on the pinned future games it calls the winner **67.4% vs 62.9%** for the placeholder and beats `p0` in every slice (log-loss 0.5854 vs 0.6026, 90% band [−0.021, −0.013]) ([[2026-11-22-main-run-results]]). The value head overfits after ≈1.2 epochs; next run: fewer correlated turns per game or a lower value weight after epoch 1. Plan: [[plan-run-v12]] (draft).
> Previously: v1.1 (`p0`, P0 changes): on 3,709 pinned future games it calls the winner **66.2% vs 62.9%** for the placeholder and beats the previous model in a paired gate (log-loss −0.011, 90% band [−0.018, −0.004]) ([[2026-11-22-p0-ab-results]]). The overnight run (`./training/overnight.sh`, now d=256 / 6 layers with the gate before install) has not been run yet.

## Goal
For any turn of a game, output (a) the win chance for each side, which drives the eval bar, and (b) a ranking of the choices, for move review. First format: Gen 9 Random Battle; then VGC 2026 Reg M-C ([[ADR-0002-format-order]]).

## v1 (built): data and inputs ([[ADR-0012-training-data-v1]])
- **Training data:** public `gen9randombattle` logs from the HolidayOugi Hugging Face dataset (2.0M games to 2026-10-05), recent months only, main server only.
- **Test data:** games collected from Showdown's API for the 14 days before 2026-11-22 (after the dataset ends), with inputlogs; also rebuilt to full information ([[ADR-0009-randbats-full-info-reconstruction]]).
- **Input:** the public view at each turn start from one player's side: 13 tokens (6 own, 6 opponent, field). Per Pokémon: species, item, ability, 4 revealed moves, Tera (ids; unknown = UNK, known-empty = NONE) and HP, fainted, active, seen, level, statuses, boosts, key volatiles. Field: turn, weather, terrain, Trick Room etc., hazards and screens per side, Tera used, and per-side totals (HP left, Pokémon alive, Pokémon unseen).
- **Targets:** value = this player won. Policy = the move id or own switch slot chosen at the turn start (pivot switches, post-faint switches, called moves and `|cant|` turns excluded).

## v1.1 changes (P0 from [[benchmark-best-in-class]], 2026-11-22)
- **Properties by id** (`training/tables.py`, buffers in the model): base stats + types per species; base power, accuracy, category, priority, type and effect flags per move (from Showdown's dex, `training/dex.json`).
- **Randbats priors** for what isn't revealed: per species, a probability-weighted mix of likely moves (top 12), items (4), abilities (3), Tera types (4), from pkmn/randbats stats (`training/randbats_gen9.json`, MIT; formes fall back to the base species).
- **Last turn's events** on the field token: per side moved first, crit, miss, super-effective, switched, fainted; plus each side's last move (id + properties).
- **Auxiliary heads** (Jaxcalibur): the opponent's choice this turn (weight 0.25) and each opposing Pokémon's item / ability / Tera / moves as revealed by the end of the game (weight 0.1 each; multi-positive loss for moves). The parser now keeps `orig_item` so a knocked-off item is still a label.
- **Smaller default:** d=256, 6 layers.
- **Measurement** (`training/metrics.py`): temperature fitted on validation and applied in the app; by-phase scores (0–2 / 3–6 / 7+ fainted); 90% bootstrap intervals over games; rating 1500+ slice; placeholder alongside. **Paired gate** `training/compare_runs.py` on a **pinned bank** of future games (`data/train/test_pinned/`, 3,709 games, 174,608 samples); both models are scored from both players' views and the files must cover exactly the same samples; the overnight script installs a model only if the gate calls it better ([[ADR-0016-two-view-scoring-strict-gate]], 2026-11-23).

## v1 model (`training/model.py`)
Transformer encoder over the 13 tokens, no positions within a side (only own / opponent / field embeddings). Value head on [field token, mean of tokens]. Policy head: move logits from the active Pokémon's token, switch logits per own token, with a mask (no fainted / active; only the first unseen slot). Loss = BCE(value) + 0.5 · CE(policy).

## Training (`training/train.py`)
AdamW, warmup then cosine, gradient clipping. Saves `last.pt` (resume), `best.pt` (best value loss: what the eval bar uses), `best_policy.pt`, `metrics.jsonl`. Every evaluation also reports the placeholder's score on the same samples, so "beats the baseline" is checked, not assumed. Time budget and SIGTERM/Ctrl-C stop cleanly.

## Overnight run (`training/overnight.sh`, [[ADR-0005-overnight-training-budget]])
Builds the full dataset (games since 2026-01-01, ≈650k games / ≈15–16M samples), trains d=256, 6 layers (≈7M params) for 9 h with `caffeinate`, scores on the pinned bank, runs the paired gate against the installed model, and installs (`training/export.py` → `data/models/current.pt`) only if the gate calls it better. Since 2026-11-23: `RUN` must be a new name, the dataset is named after its dates and checked, settings are variables, `DRY_RUN=1` checks without training or installing, `RESUME=1` continues a run ([[ADR-0016-two-view-scoring-strict-gate]]).

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
