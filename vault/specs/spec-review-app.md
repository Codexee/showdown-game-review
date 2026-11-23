---
title: Spec: review app
type: spec
status: active
tags: [area/ui]
updated: 2026-11-22
---

# Spec: review app

Lichess-style game review for Showdown games ([[project-overview]]). Runs locally ([[ADR-0001-local-web-app]]) in a Gen 4–5 pixel-art style ([[visual-style]]). Battle view: [[ADR-0011-review-screen-battle-view]].

> [!note] Status 2026-11-22: stage 4 built
> Games page and review screen work for singles and doubles, light and dark, phone and desktop. **Desktop (≥1100 × 620 px): the review screen fits one screen with no page scroll**, in three columns: battle screen + eval bar + hinge + graph | turn list | move review + what happened + team. The turn list and the review column scroll inside their panels. Narrower windows stack the columns (2026-11-23, [[2026-11-23-desktop-one-screen-layout]]). The page `index.html` is served with `Cache-Control: no-cache` so a new build always loads. **Games page (desktop ≥1000 × 600 px):** one block with profile, sync, ratings and "Add a game" in a side column beside the games list, fitted to the window; the list and the side column scroll inside the block ([[2026-11-23-games-page-one-block]]). **Symbols and motion (2026-11-23, [[2026-11-23-less-text-symbols-motion]]):** each ladder shows a format badge (generation tile + short name, coloured by family: green Random Battle, purple VGC, amber other), the Elo, GXE, and a green-vs-red wins/losses bar with the counts; game rows show the format badge, a short date ("3 h ago", "Nov 22") plus `T<turns>`, and 8×8 pixel icons with titles (lock = private, disk = saved by the userscript, scroll = full battle data, lens = reviewed) instead of text tags. Copy shortened ("Sync", "Add", "Upload a file", "Auto-save every battle"). Motion: rows rise in (220 ms, `--ease-out`, 40 ms stagger, capped at 10) on the first load and when a new game arrives, not on the 60 s refresh; ladder bars fill once per page load, stepped like the HP bars (240 ms `steps(8)`); the Sync icon turns while syncing. Reduced motion: rows fade only, no bar fill, no spin. **Review screen, same pass (2026-11-23):** header = result pip + format badge + short date + "Replay ↗" + "⇄ <opponent>"; scorecards show accuracy, verdict chips as chess marks with counts (?! inaccuracy, ? mistake, ?? blunder; ✓ when clean) and luck as a pixel dice icon with a signed number; the grading explanation and the win-chance method sit behind short disclosures ("How grading works", "<method> win chance"); "What happened" lines drop the player name (a blue/red side bar shows whose choice) and read "Choice −4.2 → Best 44%"; arrow keys shown as `kbd` glyphs. **Team paste shows only for VGC** and no longer promises exact sets (it is saved only; [[2026-11-23-codex-review]] finding 9). Motion only when a review finishes while the screen is open: scorecards rise, verdict chips follow, the graph's mistake markers pop; turn stepping stays instant (frequent, keyboard-driven). Doubles on short desktop windows (≤820 px tall) use compact HP boxes so the four never overlap. **Load and turn motion (2026-11-23, [[2026-11-23-turn-motion-and-team-paste]]):** the three columns and the turn rows rise in once when the screen opens (like the games page). Stepping **one turn forward** (and at least 180 ms after the previous step) decorates the already-final new state: HP lost drains as a pale ghost (360 ms, stepped), HP gained flashes, a hit sprite shakes, a switch-in slides in from its side, a faint drops and fades, new status / stat chips pop, the eval bar steps (now updated in place), and the turn's lines rise in order. Backward steps, jumps and held keys render instantly (measured 0.9 ms per step for 10 rapid steps, no motion classes). **Team paste** shows for every format where players build the team (`teamIsRandom` in `web/src/review.ts`: hidden only for random / Hackmons Cup / Challenge Cup / Factory formats), so VGC, OU and future formats get it. The eval is a **placeholder** (remaining HP) until stage 5. Not built: move labels (best / mistake…), best-move suggestions, forced-switch decision points mid-turn.

## Screens
1. **Games** (`#/`): trainer card (username, sync, top ladder ratings), add a game (URL, file, userscript help), your games with filters. Each row links to its review.
2. **Review** (`#/game/<id>/<step>`), a DS:
   - **Top screen:** the battle at the start of the selected turn: sprites (front for the opponent, back for you), HP boxes (name, level, HP bar, exact HP for you, % for them, status, boosts, Tera, Substitute/confusion/seeding), party balls (fainted, statused, unseen), field and side conditions. Hover an HP box for its revealed item, ability and moves.
   - **Eval bar** beside it: estimated win chance for you, blue from the bottom. After a current move review, 75% search + 25% network ([[ADR-0017-eval-bar-search-blend]]).
   - **Hinge:** previous / next, "Turn N of M".
   - **Bottom screen:** stepped eval graph (click to jump), turn list (moves of that turn, change in win chance), "What happened" (that turn's events, coloured by side).
   - Header: players, format, date, result, link to the Showdown replay, **View as the opponent**.
   - Your team paste (moved here from the games page).
   - **Move review** (stage 6, Gen 9 Random Battle only; [[ADR-0014-move-review-method]]): an *Analyze game* button runs a background job with a progress bar. When done: an accuracy card per player (verdict counts, luck), Lichess marks on turn-list rows (`?!` inaccuracy, `?` mistake, `??` blunder; the opponent's faded), a review box in "What happened" (each side's choice, verdict, points lost, the best choice, luck this turn) and graph markers on your mistakes and blunders. A result from an older model or method says so and offers to re-run. By default each player is graded on what they could see ([[ADR-0015-move-review-sampled-worlds]]); the note under the scores says which method was used.
   - Keyboard: ← → step, Home / End first and last.

## Steps
Step *k* = the state at the start of a turn plus the events that led to it: step 0 shows the leads; the last step is the end of the game. This matches a Lichess move list (position after the move, with the move shown).

## API
`GET /api/games/{id}/review?side=p1|p2` (default: your side) returns the game, the perspective, `eval_method` (`placeholder`, `model`, or `model+search`), and `steps[]` with `state` (that player's view, with sprite ids), `events`, `eval` (plus `eval_model` and `eval_search` when blended). Sprites: `GET /sprites/gen5[-back]/<id>.png`. Move review: `GET /api/games/{id}/analysis` (status `none|queued|running|done|error|unsupported`, progress, result, `stale`) and `POST` to start (`seeds` 4–128, `top_k` 2–13, `mode` `worlds` (default) or `perfect`).

## Done when (stage 4)
- [x] A saved game opens, steps turn by turn, and the bar and graph move with the values.
- [x] Works offline for archived games once sprites are cached.
- [x] Doubles layout (Codexe's VGC Reg M-C game) shows all four Pokémon.

## Related
- [[spec-eval-model]] · [[spec-replay-sync]] · [[architecture]] · [[roadmap]] · [[battle-parser]]
