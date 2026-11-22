---
title: Visual style
type: wiki
status: draft
tags: [area/ui]
updated: 2026-11-22
---

# Visual style: Gen 4–5 pixel art

Set by [[ADR-0004-pixel-art-style]]. The user asked for "a bit more aesthetic than showdown (gen4-5 pixel art style)" ([[2026-11-22-interview-round-1]]).

## Direction (draft, to settle with /frontend-design when the UI work starts)
- A DS-era (Diamond/Pearl/Platinum, Black/White) feel: chunky pixel borders on panels, a limited palette, a pixel font for headings and HP-bar-style meters.
- The **eval bar** can look like an HP bar: a green / yellow / red fill that shows one side's win chance.
- Keep body text in a clear font. Pixel fonts are hard to read at small sizes.
- Render pixel assets with `image-rendering: pixelated` at whole-number scales (2×, 3×).

## Assets
- Pokémon battle sprites: Showdown's own sprite sets (including Gen 5 animated sprites) are served from `play.pokemonshowdown.com/sprites/`. (unverified) Use them for battle display rather than drawing new ones.
- Our own original art (frame borders, icons, background tiles, the eval bar): generate with **SpriteCook** ([[tooling]]). Not installed yet.
- Do not copy Nintendo or Game Freak UI art directly. Use the era's style with original assets.

## Related
- [[spec-review-app]] · [[tooling]] · [[ADR-0004-pixel-art-style]]
