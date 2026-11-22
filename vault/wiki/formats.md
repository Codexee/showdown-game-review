---
title: Formats in scope
type: wiki
status: active
tags: [area/model, area/data]
updated: 2026-11-22
---

# Formats in scope

Order set by [[ADR-0002-format-order]].

## 1. [Gen 9] Random Battle (first target)
- Chosen over [Gen 9 Champions] Random Battle on 2026-11-22 ([[2026-11-22-interview-round-2]]).
- Showdown id: `gen9randombattle`. Singles, 6v6, random teams, no team preview. (unverified: the id comes from foul-play's README examples, [[2026-11-22-research-findings]])
- Not chosen: **[Gen 9 Champions] Random Battle** (`mod: 'champions'`, `team: 'random'`, `bestOfDefault: true`) ([[2026-11-22-research-findings]]).

Why randbats is a good first target:
- Each side's sets come from Showdown's random-set generator, so the model can know the full pool of possible sets for each species instead of guessing from usage stats. (unverified)
- foul-play plays `gen9randombattle` out of the box, so it is a ready opponent and baseline ([[bot-landscape]]).
- The 1.5% usage filter does not apply: the species pool is set by the generator, not by player choice ([[2026-11-22-interview-round-2]]).

## 2. [Gen 9 Champions] VGC 2026 Reg M-C (second target)
- Doubles (VGC). Exists in Showdown's `formats.ts`, also as a Bo3 variant ([[2026-11-22-research-findings]]).
- Smogon publishes `gen9championsvgc2026regmc-{0,1500,1630,1760}.txt` usage files for 2026-10 ([[2026-11-22-research-findings]]).
- No strong open-source doubles engine like foul-play exists. AlphaMon is the closest reference ([[bot-landscape]]).
- Action space per turn is much larger than singles (two Pokémon, targets, spread moves).
- Training keeps only species and moves at ≥1.5% usage ([[2026-11-22-interview-round-2]]).

## Earlier target: [Gen 9 Champions] OU (superseded as first target)
- `mod: 'champions'`, `ruleset: ['Standard']`, banlist: AG, Uber, Moody, Damp Rock, King's Rock, Light Clay, Quick Claw, Baton Pass, Last Respects, Shed Tail ([[2026-11-22-research-findings]]).
- 6v6 singles with Mega Evolution. 106,694 battles in the 1500 stats file for 2026-10; 66 species at ≥1.5% usage ([[2026-11-22-research-findings]]).
- Kept here because its usage data and replay counts are already collected. It may come back later.

## Related
- [[data-sources]] · [[bot-landscape]] · [[spec-eval-model]] · [[ADR-0002-format-order]]
