---
title: ADR-0015 Move review over sampled worlds
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model, area/ui]
---

# ADR-0015: Grade each player on what they could see (sampled hidden sets)

Amends [[ADR-0014-move-review-method]] item 2 (transitions). The rest of ADR-0014 stands.

## Context
- ADR-0014 plays every choice pair with both teams' real sets. A grade could then use what the player could not know, for example an unrevealed Choice Scarf or coverage move ([[open-questions]] #6).
- PS Dashboard, Jaxcalibur and mikumiku37 all search over sampled "worlds" of hidden information ([[2026-11-22-prior-art-research]], [[2026-11-22-prior-art-jaxcalibur-mikumiku]]).
- The randbats set data (`training/randbats_gen9.json`, pkmn/randbats stats) gives, for each species, its roles with weights and each role's move, item, ability and Tera type rates.

## Decision
1. **Worlds per graded player.** To grade player X at a turn, draw W worlds (default 16) of the opponent's hidden information as X saw it at the turn start (`server/review/worlds.py`):
   - for each opposing Pokémon already seen: pick a role with weight × the chance of every revealed move, item, ability and Tera type under it; keep the revealed facts; fill the moves up to 4 (moves the role always has first, then by their rates), and draw the item, ability and Tera type if unrevealed.
2. **Simulator.** `tools/review-engine.cjs` writes the world into the restored turn-start battle (move slots with full PP for new moves, item, ability, Tera type) and rebuilds the requests. Each world has its own dice seed.
3. **Matrix per world.** In each world the opponent knows its own set: its candidates are ranked by the policy head within that world, and X's choice is valued against the opponent's equilibrium answer in that world. X's value for a choice is the average over worlds. Regret, bands and softening follow ADR-0014.
4. **Luck in the real game.** Luck stays "what happened minus what the two played choices make likely", measured with the real sets (the played pair, S seeds).
5. **Default.** `mode: "worlds"` is the default; `mode: "perfect"` (ADR-0014) remains for comparison. Results are tagged `version: 2`, so older results show as stale.

## Known limits
- Opposing Pokémon not yet seen keep their real species and set (changing a species inside the simulator is not done). When the opponent switches to an unseen Pokémon, the grade still uses the real one.
- Role-level item rates approximate Showdown's item code (items depend on the moves drawn).
- A world with an unrevealed Choice item does not add a choice lock that the real game didn't have.

## Consequences
- About 2.5× the simulator work of ADR-0014 (77 s against 31 s for the test game).
- Measured on 12 random games ([[2026-11-22-worlds-vs-perfect-results]]): 79% of 608 verdicts unchanged, 6% flagged in one mode only, regret difference mean 0.8 points (max 18.7). Worlds mode against itself (16 vs 32 worlds) changes 2% of flags, mean 0.24, so most of the change is the hidden information, not noise.
- Close calls (within about 1 point of a band) can still flip between runs. More worlds lower the noise (by sampling theory, 32 worlds cut its spread by about 30%, unmeasured) at proportionally more time.

## Related
- [[ADR-0014-move-review-method]] · [[spec-review-app]] · [[module-map]] · [[benchmark-best-in-class]]
