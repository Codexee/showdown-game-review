---
title: Stage 5 data sizing and test training runs
type: raw
date: 2026-11-22
source: commands in session 15119347 (training/*.py); outputs in data/models/test, test2 (git-ignored)
---

# Stage 5: data sizing and test runs (raw)

Do not edit. Synthesized into [[spec-eval-model]] and [[ADR-0012-training-data-v1]].

## Data
- Upload rate: 256 recent public `gen9randombattle` replays spanned 7.5 h → **≈34 per hour**.
- **HolidayOugi/pokemon-showdown-replays** (HF): 11 parquet parts for `[Gen 9] RANDOMBATTLE`, 4.49 GB, downloaded in ~50 s. Columns: id, format, players, log, uploadtime, views, formatid, rating; **no inputlog**; no license stated. **2,012,698 rows** (1,446,502 with a rating); ids 99.5% main server (smogtours, rom, radicalred, impulse, gpl...). Per month (2026): Jan 50k, Feb 51k, Mar 71k, Apr 59k, May 97k, Jun 117k, Jul 93k, Aug 59k, Sep 70k, Oct 9.7k (cutoff 2026-10-05).
- Other datasets checked: jakegrigsby/metamon-raw-replays (2.68M replays, no randbats files listed), milkkarten/pokemon-showdown-replays-merged (29M, Gen 9 RANDOMBATTLE 703k; filters games ≤4 or ≥96 turns).
- Collector (`training/collect`, 1 req/s): ~55 replays/min; 1,231 saved in the first 22 min, 0 errors.
- Rebuild of the first 1,283 collected games (all at commit ac7b7da0f9): 1,282 exact, 1 mismatch caused by an `|error|` line (a chat command typed in the battle room); after adding `error` to the server-only lines, it matches too. 28 s.

## Features and speed
- Sample: 13 tokens (6 own, 6 opponent, 1 field); 8 ids + 27 numbers per Pokémon; 36 (later 42) field numbers. Vocab from Showdown data at ac7b7da0f9: 1,518 species, 954 moves, 587 items, 321 abilities, 19 types.
- `parse + encode`: 22 ms/sample cold; 0.27 ms warm; 0.04 ms after removing a redundant `deepcopy` in `BattleState.snapshot` (asdict already deep-copies).
- Dataset build: part11 (12,571 games) → 304,058 samples in 3 s; Aug–Oct 2026 (137,912 games) → 3,227,661 samples in 34 s (13 workers).

## Test run 1 (`test`): 12.6k games, 4.27M params, 6 min
- Policy learned fast (val top-1 0.37, top-3 0.73). Value overfit after ~2 epochs (val loss 0.66 → 2.35); best value acc ≈ 0.62.
- Training loss showed `inf` from a few policy targets on slots the switch mask rules out → those samples are now skipped (0 of 920 in validation).
- **Placeholder on the same validation set: log-loss 0.631, acc 0.636 — better than the model.** → Added per-side totals (HP, alive, unseen) to the field token and reported the placeholder in every evaluation.

## Test run 2 (`test2`): 138k games (Aug–Oct 2026), 4.27M params, 12 min, ~10.5k samples/s on MPS
| step | val value loss | val acc | ECE | policy top1 / top3 |
|---|---|---|---|---|
| 1000 | 0.5917 | 0.670 | 0.028 | 0.314 / 0.680 |
| 3000 | 0.5777 | 0.681 | 0.010 | 0.390 / 0.754 |
| 6000 | 0.5746 | 0.686 | 0.015 | 0.460 / 0.810 |
| 7234 | 0.5763 | 0.683 | 0.017 | 0.474 / 0.822 |
Placeholder on the same validation set: **0.6265 / 0.645**.

## Test2 on future games (1,336 collected games, Nov 2026, both sides, 62,582 samples)
- Model: value loss **0.6159**, acc **0.657**, Brier 0.2107, ECE 0.031; policy top1 0.473, top3 0.823.
- Placeholder: 0.6344, acc 0.635.
- Value acc by turn: 1–5: 0.565; 6–15: 0.653; 16+: 0.706.
- The value head's edge shrinks from validation (+4.1 acc points) to future games (+2.2). Likely cause: drift (random sets changed after the dataset's Oct 5 cutoff). The policy head held.

## Overnight model benchmark
- d=384, 6 layers, ff 1536, bs 2048: 12.59M params, ≈4.5k samples/s, no memory issues.
