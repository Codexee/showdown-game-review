---
title: ADR-0009 Rebuild full-information randbats games from inputlogs
type: adr
status: proposed
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/model, area/data]
---

# ADR-0009: Rebuild full-information Gen 9 Random Battle games from replay inputlogs

## Context
- For random formats, the replay JSON includes the **inputlog**: the Showdown commit hash (`>version`), the battle seed, each player's team seed, and every choice ([[2026-11-22-research-round-2]]).
- The `>version` hash is a real commit in smogon/pokemon-showdown.
- A normal replay log shows only what was revealed during the game. Metamon has to guess hidden sets when it rebuilds each player's view ([[bot-landscape]]).

## Decision (proposed; needs a quick prototype)
- For each archived `gen9randombattle` replay, run Showdown's simulator **at the commit named in `>version`** with the inputlog's seeds and choices. This should reproduce both full teams (moves, items, abilities, Tera types, EVs) and the exact battle, turn by turn.
- Training then uses **both** views of each turn:
  - the player's partial view, as the model input;
  - the full hidden state, as extra targets (predict the opponent's sets) and as a check that the rebuild matches the public log.
- Use pkmn's randbats stats (`data.pkmn.cc/randbats/stats/gen9randombattle.json`) as set priors when the full state is not known, i.e. at review time ([[spec-eval-model]]).

## Risks and checks
- Random team generation changes often. Rebuilding needs the exact commit; keep a small cache of Showdown checkouts keyed by commit, or group replays by commit. **Unknown:** how many distinct commits a few weeks of replays span.
- Verify by comparing the rebuilt battle's protocol output with the replay's public log, line by line. Drop any replay that doesn't match.
- This applies only to random formats. VGC Reg M-C replays have no safe inputlog and need the Metamon-style partial-view method plus open team sheets, if available. (unverified for M-C)

## Consequences
- If it works, randbats training data has exact labels for hidden information, which is better than what Metamon had.
- Adds a Node step (running the simulator at past commits) to the data pipeline.

## Related
- [[spec-eval-model]] · [[data-sources]] · [[formats]]
