---
title: Battle log parser (stage 3)
type: wiki
status: active
tags: [area/data, area/model]
updated: 2026-11-22
---

# Battle log parser

Turns a Showdown protocol log into the battle state at the **start of every turn**, plus the final state. Code: `server/battle/` ([[module-map]]). It serves the review screen ([[spec-review-app]]) and training ([[spec-eval-model]]).

## Accuracy
Graded against Showdown's own simulator on 261 real `gen9randombattle` games ([[2026-11-22-parser-accuracy-results]]):
- **Unbiased** (fresh data, before any fixes from it): **96/100 games and 99.4% of turn states** with no error.
- After fixing what each set showed: 261/261 games, 6,200/6,200 states. The fixes are general Showdown mechanics, not special cases for single games.
- Not graded: doubles / VGC (no inputlog to rebuild truth from). Codexe's VGC game parses plausibly. Treat doubles as **unverified** until a doubles truth source exists.

## What a state holds
Per side: name, team size, every Pokémon seen (or listed in team preview), side conditions with layers. Per Pokémon: species (current forme) and base forme, level, gender, HP (`hp`/`maxhp`, `hp_exact`), status, fainted, active + position, boosts, tracked volatiles, item, ability (+ original ability), revealed moves, Tera. Field: weather, terrain, pseudo-weather (Trick Room etc.). Ids are Showdown ids (`to_id`).

**Unknown vs known-empty:** `item: null` = not revealed; `item: ""` = revealed gone (knocked off, eaten, flung). Same for ability (`null` = unknown).

## Views
`view_for(state, "p1"|"p2", format_id)`: what that player could see. Replay logs can show exact HP for both sides; the view converts the opponent's HP to Showdown's displayed percentage:
- Gen 9 (non-Champions): `ceil(100·hp/maxhp)`, but 99 unless at full HP.
- Champions formats: `floor(100·hp/maxhp)`, at least 1 (from `sim/pokemon.ts` `getHealth`).

API: `GET /api/games/{id}/turns?side=p1|p2|all` (default: your side).

## Known limits (not knowable from a log)
- **Silent Regenerator / Natural Cure** on switch-out: applied only when the ability is known. Most remaining differences are Regenerator heals before the ability was revealed. Possible improvement: in randbats, infer the ability from the species' possible abilities in the set data ([[data-sources]]).
- **Illusion:** until Zoroark is revealed, the state shows what players believed. On `|replace|`, moves and HP move to Zoroark. If it leaves unrevealed, the disguise's name keeps the Zoroark's HP and moves.
- Not tracked yet: PP, Wish / Future Sight / slot conditions, weather and screen turn counts, move-locking (Choice), types after Protean / Soak.

## Mid-turn decisions
States are taken at `|turn|` only. Forced switches after a faint happen mid-turn and are not separate states yet. The review screen and training can add them later.

## Related
- [[2026-11-22-parser-accuracy-results]] · [[ADR-0009-randbats-full-info-reconstruction]] · [[module-map]] · [[2026-11-22-bug-forme-change-team]]
