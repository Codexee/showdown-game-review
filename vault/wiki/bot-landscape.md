---
title: Bot landscape
type: wiki
status: active
tags: [area/model]
updated: 2026-11-22
---

# Bot landscape

All facts from [[2026-11-22-research-findings]] unless marked.

| Project | What it is | Formats | Use for us |
|---|---|---|---|
| **foul-play** (pmariglia) | Search bot on poke-engine (Rust), expectiminimax / MCTS | Singles only. Supports `gen9randombattle` and Champions (`gen9champions` generation) | Baseline opponent and teacher for Gen 9 Random Battle. Could label positions with search values. |
| **poke-env** (hsahovic) | Python framework for bots; Gymnasium envs; `DoubleBattle` class (unverified) | Singles and doubles | Base for our agent, battle-state parsing and self-play. |
| **Metamon** (UT-Austin-RPL) | Offline RL with transformers on 3.5M–5M+ human trajectories, plus 20M+ self-play. RLC 2025 paper. | Gen 1–4 OU and Gen 9 OU; no Champions | Copy the method: reconstruct each player's view from replays, then imitation learning followed by offline RL. Its value head gives a win estimate. |
| **AlphaMon** (davidemodolo) | Transformer policy/value model plus Monte Carlo rollout search, trained on replays | Doubles | Main reference for the VGC M-C stage. |
| **FutureSight AI** (prayush-sinha) | Simultaneous expectiminimax plus Set-Transformer pruning (ONNX), Smogon priors | Singles (unverified) | Ideas for set inference and pruning. |
| **pokemonshowdown-ai** (taylorhansen) | RL | Gen 4 random battles | Small reference only. |
| **Showdown random AI** | `sim/tools/random-player-ai.ts` | Any | Weakest baseline. |

## What we take from this
- **Eval = value head.** The eval bar is the model's predicted win chance for one side at each turn. Metamon and AlphaMon both train a value output. See [[spec-eval-model]].
- **Replays are seen from one side.** Metamon rebuilds each player's partial view from a public replay. Our parser needs the same step.
- **Search on top.** AlphaMon and foul-play add search at play time. For review, a value estimate per turn is enough at first; search can rank alternative moves later.

## Related
- [[formats]] · [[spec-eval-model]] · [[data-sources]]
