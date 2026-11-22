---
title: ADR-0013 Post-game analysis only
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/ui, area/model]
---

# ADR-0013: The app analyzes finished games only; no live help during a battle

## Context
- The two strongest bots in our formats (Jaxcalibur, mikumiku37) withheld code and weights because strong engines can be used to cheat on the ladder and in tournaments ([[2026-11-22-prior-art-jaxcalibur-mikumiku]]). Community commentary calls tournament use "a no-go" while welcoming review and practice uses.
- Our userscript runs on play.pokemonshowdown.com, and our model gives win chances and (in stage 6) best-move suggestions.

## Decision
- Analysis is **post-game only**. The userscript sends a battle log only after `|win|` / `|tie|` (or as incomplete after the room closes), and the app shows no evaluation for a battle in progress.
- No feature will feed evaluations or move suggestions into a live battle (no overlay on live battle rooms, no API for in-progress positions).
- This formalizes how the app already behaves ([[spec-replay-sync]]); any future feature that touches live battles needs a new ADR.

## Consequences
- The review tool stays a study aid, like chess engines used after the game.
- Before sharing the model or the app beyond personal use, revisit release questions (weights, a public engine endpoint) with this ADR in mind.

## Related
- [[benchmark-best-in-class]] · [[spec-review-app]] · [[ADR-0006-replay-archive]]
