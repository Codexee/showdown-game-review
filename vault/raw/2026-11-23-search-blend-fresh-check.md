---
title: Search blend weight, fresh-sample check
type: raw
source: local run 2026-11-23 03:12–04:00 EST, data/models/search_eval/worlds-fresh.jsonl
tags: [area/model]
created: 2026-11-23
---

# Search blend weight on fresh games (2026-11-23)

Games 200–299 of the same seed-0 shuffle of the pinned bank (none used to pick the weight), worlds mode, `main@9000`, 6 workers, 130 s per game. 100 games, 2,456 turns. Network log-loss 0.6059 (accuracy 67.3%); search alone 0.6033 (67.8%).

| Search weight | Change vs network | 90% band (over games) |
|---|---|---|
| 0.50 | −0.0053 | [−0.0084, −0.0027] |
| 0.60 | −0.0058 | [−0.0095, −0.0026] |
| 0.70 | −0.0062 | [−0.0104, −0.0024] |
| **0.75** | **−0.0063** | **[−0.0109, −0.0022]** |
| 0.80 | −0.0063 | [−0.0113, −0.0020] |
| 0.90 | −0.0062 | [−0.0118, −0.0013] |
| 1.00 | −0.0026 | [−0.0112, +0.0075] |

The 0.75 weight from the first 199 games holds: the gain is smaller (−0.0063 against −0.0083) but the whole band is below zero, and 0.7–0.8 is a flat optimum. Search alone is not reliably better than the network on either sample; the blend is.
