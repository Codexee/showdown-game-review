---
title: ADR-0002 Format order
type: adr
status: accepted
date: 2026-11-22
supersedes: "Champions OU as the target format (stated in chat on 2026-11-22, before the interview; no earlier ADR)"
superseded_by:
tags: [area/model]
---

# ADR-0002: Gen 9 Random Battle first, then Champions VGC 2026 Reg M-C

## Context
- First request: a VGC bot ([[2026-11-22-interview-round-1]]).
- Next request: "the target format is champions ou", with training focused on species and moves at ≥1.5% usage.
- The interview pointed out that Champions OU is singles, not VGC. The user answered: "try gen9 randbats, then vgc m-c."

## Decision
1. Build and train for **Gen 9 Random Battle** first.
2. Then **[Gen 9 Champions] VGC 2026 Reg M-C** (doubles).

Champions OU is no longer the first target.

> [!note] Clarified 2026-11-22
> "gen9 randbats" means standard [Gen 9] Random Battle (`gen9randombattle`), not [Gen 9 Champions] Random Battle ([[2026-11-22-interview-round-2]]).

## Options considered
- **Champions OU singles:** good usage data, foul-play support. Dropped as first target by the user.
- **Randbats first (chosen):** simpler for a first model. Known set pools, a ready opponent (foul-play), a lot of games.
- **VGC M-C directly:** what the user wants long-term, but doubles is much harder, with no strong open-source engine.

## Consequences
- The parser and model must be built so that the doubles stage reuses them (battle state, embeddings, training loop).
- The 1.5% usage filter does not apply to randbats; it does apply to VGC M-C ([[2026-11-22-interview-round-2]]).

## Related
- [[formats]] · [[spec-eval-model]] · [[bot-landscape]]
