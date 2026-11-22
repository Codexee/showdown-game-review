---
title: ADR-0011 Review screen draws its own turn-by-turn battle view
type: adr
status: accepted
date: 2026-11-22
supersedes:
superseded_by:
tags: [area/ui]
---

# ADR-0011: The review screen draws its own turn-by-turn battle view

## Context
The review screen needs to show the battle next to the eval bar and graph ([[spec-review-app]]). [[spec-review-app]] had left open whether to embed Showdown's animated replay player. The user chose our own view and asked to build the pixel art now and add SpriteCook later ([[2026-11-22-stage4-answers]]).

## Decision
- Draw a Gen 4–5 style battle box from the parsed state of each turn ([[battle-parser]]): sprites, HP bars, status, boosts, field and side conditions, plus that turn's log lines as text.
- It steps **by turn**, the same unit as the eval bar, eval graph and turn list.
- Pokémon sprites come from Showdown's sprite server through a local caching proxy (`/sprites/...`), so a game viewed once works offline afterwards.
- UI art (frames, bars, icons) is CSS/SVG pixel art for now; SpriteCook may replace it later ([[tooling]]).
- The eval bar shows a **placeholder** estimate (labelled as such) until the model exists ([[spec-eval-model]]).

## Options considered
- **Own view (chosen):** our look, works offline, in sync with our per-turn states; no move animations.
- **Embed Showdown's player:** full animations, but Showdown's look, needs the internet, and steps by animation frames instead of our turn states.

## Related
- [[spec-review-app]] · [[visual-style]] · [[ADR-0004-pixel-art-style]]
