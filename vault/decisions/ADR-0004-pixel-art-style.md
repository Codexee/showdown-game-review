---
title: ADR-0004 Pixel-art style
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/ui]
---

# ADR-0004: Gen 4–5 pixel-art visual style

## Context
The user wants the app "a bit more aesthetic than showdown (gen4-5 pixel art style, find and use a pixel art skill for when we get to this)" ([[2026-11-22-interview-round-1]]).

## Decision
- The UI uses a DS-era (Gen 4–5) pixel-art look with original assets. Details in [[visual-style]].
- Original art is made with the **SpriteCook** plugin, the closest pixel-art tool found ([[tooling]]). It is installed when the UI stage starts.
- Pokémon sprites come from Showdown's sprite sets, not new drawings.

## Consequences
- Adds an asset-making step to the UI stage.
- Pixel fonts cut readability, so body text stays in a clear font.

## Related
- [[visual-style]] · [[spec-review-app]] · [[ADR-0001-local-web-app]]
