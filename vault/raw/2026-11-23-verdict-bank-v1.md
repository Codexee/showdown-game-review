---
title: Verdict bank v1 results
type: raw
source: local run 2026-11-23 12:35-14:29 EST, data/verdict_bank/ (training/verdict_bank.py)
tags: [area/model]
created: 2026-11-23
---

# Verdict bank v1 (2026-11-23)

Model `v12@36000`. 60 random pinned-bank games (seed 0, custom-rule games skipped) graded at the default settings (worlds mode, 16 worlds per side, top 6 choices per side): 179.8 s per game with 8 workers. From their graded choices, 69 picked (38 games): flagged 21, close to a band edge (±1 point of 5/10/20) 14, switches 10, Tera 7, small endgames (≤3 left a side) 7, good 10. Pools: flagged 380, close 255, switch 387, Tera 81, endgame 524.

## Default vs high-effort reference (64 worlds per side, top 13 choices: every legal option)
- Same flagged/not: **92.8%**; same band: 87.0%; same best choice: 85.5%.
- Regret difference: mean **0.61** points, max 5.11.
- Flagged by the default only: 4; by the reference only: 1.
- By category, same flag: close calls 78.6%, flagged 90.5%, everything else 100% (switch, Tera, endgame, good).

## Default vs default with independent seeds (noise)
- Same flagged/not: **89.9%**; same band 88.4%; same best choice 94.2%.
- Regret difference: mean **0.48**, max 3.69. Flag flips: 7 of 69 (4 one way, 3 the other).
- By category, same flag: close 78.6%, flagged 85.7%, switch 90%, others 100%.

## Reading
- Most of the gap to the reference is sampling noise: an independent re-run at the same effort disagrees about as often (10.1% flag flips) as the reference does (7.2%).
- Pruning to the top 6 changes the best choice 14.5% of the time but rarely changes a flag.
- The bank was picked from the default's own verdicts, so "flagged" items lean towards regression to the mean (default flagged 4 the reference didn't, 1 the other way).
- The reference shares the method's biases (one dice roll per world, separate solves per world, depth 1); it can't measure those.
