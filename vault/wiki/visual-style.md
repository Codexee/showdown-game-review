---
title: Visual style
type: wiki
status: active
tags: [area/ui]
updated: 2026-11-23
---

# Visual style: Gen 4–5 pixel art

Set by [[ADR-0004-pixel-art-style]]; the review screen's battle view by [[ADR-0011-review-screen-battle-view]]. Direction set with `/frontend-design` on 2026-11-22 ([[2026-11-22-stage4-answers]]). Code: `web/src/style.css`.

## The one bold idea
The review screen is a **DS**: a top screen (the battle) and a bottom screen (eval graph, turns, what happened), joined by a **hinge** that holds the turn controls. The eval bar stands beside the top screen like an HP bar on its end. Everything else stays quiet.

## Tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| `--frame` | `#24375A` | `#0A1222` | DS frame, panel borders (Gen 4 text-box navy) |
| `--screen` | `#EEF3F8` | `#1B2740` | screen and panel background |
| `--grass-1/2`, `--sky-1/2` | grass `#A8DC86` / `#79BC5E` | night teal `#2C5566` / `#1E3A4A` | battle field |
| `--hp-green/yellow/red` | `#3CC468` / `#F5C032` / `#E34040` | same | HP bars (green > 50%, yellow > 20%) |
| `--you` / `--them` | `#3B7DD8` / `#D23A56` | `#6AA2F0` / `#F0708A` | the two sides everywhere (eval bar, graph, HP box borders, event lines) |
| `--btn` | `= --frame` | `#3D6098` | buttons (lighter than the screen in dark mode) |

Pixel frame: a thick border with the four corner pixels cut away (`clip-path`, `--px: 4px`). No soft shadows, no blur. HP and eval bars animate in 8 steps, not smoothly; reduced motion turns this off.

## Type
- **DotGothic16** (pixel, one weight) for headings, numbers, HP, levels, turn counters. A Japanese dot-matrix gothic, close to the type DS games used. `font-synthesis-weight: none` stops fake bold.
- **Atkinson Hyperlegible** for everything you read: event text, labels, help.
- Both self-hosted with `@fontsource`, so the app works offline.
- **Pixelify Sans was tried first and rejected:** its "5" reads as "S" and its bold "C" as "O" ("Turn 4 of 2S", "Oodexe"). Numbers are the pixel font's main job.

## Assets
- Pokémon: Showdown's Gen 5-style sprites (front for the opponent, back for your side), through the local caching proxy `/sprites/gen5[-back]/<id>.png`. 192 px (2×) in singles, 144 px in doubles, 96 px on phones.
- UI art is CSS only (frames, HP bars, party balls, field). No Nintendo UI art is copied.
- **SpriteCook** (plugin, not installed): planned to replace the CSS art with generated sprites/UI kit later ([[tooling]]).

## Rules kept
- Status abbreviations (BRN, PAR…) stay in capitals: game vernacular, not decoration.
- Meta details are separate elements with gaps, not joined by middle dots.
- Text left-aligned; line lengths short; visible focus ring (`--focus`, yellow).

## Rule: official Pokémon sprites only (user, 2026-11-23)
Battle elements get a picture only when the Pokémon games have an official sprite for it: Pokémon (gen5 still and animated), item icons, the substitute doll. Not Showdown's own effect art (`/fx/` rocks, caltrops, web) and not hand-drawn CSS art; anything else (hazards, screens, Tailwind, weather, terrain, rooms) is a tag or an icon; the drawn field layers were removed on the user's answer ([[2026-11-23-remove-field-layers]]) ([[2026-11-23-official-sprites-and-space]], corrected by [[2026-11-23-official-means-pokemon-sprites]]).

> [!warning] Corrected
> The first reading of "official sprites" (Showdown's `/fx/` images) was wrong; the user meant official Pokémon sprites ([[2026-11-23-official-means-pokemon-sprites]]).

## Rule: icons over text labels (user, 2026-11-23)
Use an icon or symbol instead of a text label wherever the symbol reads clearly; put the words in `aria-label` and `title` ([[2026-11-23-icons-over-text-rule]], [[2026-11-23-less-text-symbols-motion]]). Examples in the app: the pin, ⟳ Sync, the dice for luck, chess marks (?!, ?, ??) for verdicts, pixel icons for game tags (lock, disk, scroll, lens), green/red bars for wins and losses, type-coloured chips. Pixel icons live in `ICONS` (`web/src/list.ts`), drawn 1:1 on an 8×8 or 14×14 grid.

## Related
- [[spec-review-app]] · [[ADR-0011-review-screen-battle-view]] · [[tooling]]
