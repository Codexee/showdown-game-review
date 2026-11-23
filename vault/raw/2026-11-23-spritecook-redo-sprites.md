---
title: Redo the sprites with SpriteCook where it applies and helps
type: raw
source: user message in chat, 2026-11-23
tags: [area/ui]
created: 2026-11-23
---

User, verbatim: "redo the sprites with spritecook when applicable and useful"

State when asked (Claude, 2026-11-23): SpriteCook is not installed (not in the user's plugins; no SpriteCook tools in the session). The install card was shown earlier the same day ([[2026-11-23-open-questions-2-to-5]]).

Reading recorded by Claude, against the sprite rules in [[visual-style]] ([[2026-11-23-official-means-pokemon-sprites]], [[2026-11-23-remove-field-layers]], [[2026-11-23-audit-fixes-go-sprite-project-official]]):
- **Applicable (interface art, not battle visuals):** the 13 pixel icons in `ICONS` (`web/src/list.ts`: lock, disk, scroll, dice, grid, pin, pinoff, sun, moon, motion, drop, sync, lens); an app icon / favicon (none exists; `GET /favicon.ico` falls through to index.html, noted in the 2026-11-23 session log); possibly the panel / DS frame and HP-box frame as 9-slice art (now CSS `clip-path`).
- **Not applicable:** Pokémon, party minis, items, the substitute doll (official sprites already); field background, platforms, hazards, screens, weather, terrain (rule: official sprites or tags only, drawn field layers removed).
- **Keep in mind:** the current icons use `currentColor`, so they follow the light/dark theme; generated colour icons would need a version per theme or a palette that works on both.
