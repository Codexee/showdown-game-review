---
title: Log parser accuracy vs the simulator
type: raw
date: 2026-11-22
source: tools/compare_parser.py runs in session 15119347; data in data/proto (git-ignored)
---

# Log parser accuracy vs Showdown's simulator (raw)

Do not edit. Synthesized into [[battle-parser]].

## Method
- `tools/sim-states.cjs` replays each inputlog at its commit and dumps the TRUE state at every turn start plus the end: HP, status, active slot, boosts, item, ability, Tera, base moves, volatiles, side conditions, weather, terrain, pseudo-weather.
- `tools/compare_parser.py` checks every field the parser has seen. An unrevealed item or ability is not an error; revealing a wrong one is. Moves: every parsed move must be in the true moveset.
- Differences that no log reader could know at that moment are counted separately as "not knowable": a silent Regenerator heal when the ability was never revealed, and Zoroark's Illusion before (or without) its reveal.

## Runs (all gen9randombattle; 3 Showdown commits)
| Set | Games | Turn states | State when graded | Games with 0 errors | States with 0 errors |
|---|---|---|---|---|---|
| Tuning set (60 newest + Codexe's game) | 61 | 1,199 | first version | 0/61 | 790/1,199 (65.9%) |
| Tuning set | 61 | 1,199 | after fixes from this set | 61/61 | 1,199/1,199 |
| **Holdout 1** (next 100, older) | 100 | 2,529 | **first look, unbiased** | **88/100** | **2,456/2,529 (97.1%)** |
| Holdout 1 | 100 | 2,529 | after its fixes | 100/100 | 2,529/2,529 |
| **Holdout 2** (next 100, older) | 100 | 2,472 | **first look, unbiased** | **96/100** | **2,457/2,472 (99.4%)** |
| All three sets | 261 | 6,200 | final | 261/261 | 6,200/6,200 |

Not-knowable differences in the final run: 28 + 224 + 207 (mostly silent Regenerator heals on Pokémon whose ability was never revealed).

## Bugs found and fixed, by round
- **Tuning:** `[Gen 9] Random Battle` read as a `[tag]`; `|start` routed to the `-start` handler; fainting must clear active/boosts/volatiles/Tera (the sim `delete`s `terastallized` on faint) and restore the base ability; a berry's `[from] item:` line after `-enditem` re-revealed it; As One (Calyrex) shows as Unnerve + Grim Neigh; moves used while Transformed aren't the user's own; Imposter copies the target's ability; `|replace|` has no HP field, so Zoroark takes the disguise's HP; forme changes set abilities silently (Mega, Terapagos), now handled with a table of 126 in-battle formes from Showdown's pokedex; a Bo3 randbats game has team preview and the sim keeps only the chosen Pokémon.
- **Holdout 1:** an empty HP field in `-formechange` (Minior) was read as 0 HP; Slow Start isn't a sim volatile; `-activate|item: Leppa Berry|...|[consumed]` after `-enditem` re-revealed it; `|cant|X|ability: Queenly Majesty|MOVE|[of] Y` means MOVE is Y's; Glaive Rush (`-singlemove ... [silent]`) has `duration: 2`.
- **Holdout 2:** Terapagos / Ogerpon go back to their base forme with a `[silent] detailschange` on faint, and their ability returns to the pre-forme ability.

## Other observations
- Uploaded randbats replay logs show exact HP for both sides; the Champions VGC Reg M-C replay (Codexe's) shows percentages (`72/100`). The parser handles both.
- Codexe's VGC game parses plausibly (no simulator truth available: no inputlog for non-random formats): doubles positions, Floette → Floette-Mega with Floettite + Fairy Aura, Palafin-Hero with Zero to Hero, two Intimidate drops.
