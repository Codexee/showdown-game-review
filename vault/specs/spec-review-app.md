---
title: Spec: review app
type: spec
status: draft
tags: [area/ui]
updated: 2026-11-22
---

# Spec: review app (draft)

Lichess-style game review for Showdown games ([[project-overview]]). Runs locally ([[ADR-0001-local-web-app]]) in a Gen 4–5 pixel-art style ([[ADR-0004-pixel-art-style]], [[visual-style]]).

## Screens
1. **Profile and game list:** ratings plus the games list from [[spec-replay-sync]].
2. **Review screen** for one game:
   - Battle view that plays the replay turn by turn. Plan: use Showdown's own replay/battle client code or the `@pkmn` libraries for animations. (unverified which works best; check licences)
   - **Eval bar** next to the battle: win chance for the user's side after each turn, styled like an HP bar.
   - **Eval graph** under it: win chance over all turns. Click a point to jump to that turn.
   - **Turn list**: each choice with a label (best / good / inaccuracy / mistake / blunder) based on the win-chance drop, plus the model's preferred move. (Labels come in roadmap stage 6.)
   - Keyboard: ←/→ for previous/next turn.

## API (local server)
- `GET /api/profile` · `GET /api/games?format=&result=` · `GET /api/games/<id>` (log plus metadata) · `GET /api/games/<id>/eval` (per-turn values; computed once and cached) · `POST /api/sync`.

## Done when
- A saved game opens, plays turn by turn, and the bar and graph move with the model's values.
- Works offline for archived games.

## Related
- [[spec-eval-model]] · [[spec-replay-sync]] · [[architecture]] · [[roadmap]]
