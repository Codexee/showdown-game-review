---
title: Design audit results (Codex and Claude)
type: raw
source: Codex CLI (read-only, via codex-rescue agent) and Claude (browser pane), 2026-11-23
tags: [area/ui]
created: 2026-11-23
---

Requested in [[2026-11-23-bigger-vgc-sprites-and-design-audit]]. Codex could not reach the local server and audited from the code; Claude measured in the browser at 1440×900, 1440×790, 900×800 and 375×812, light and dark.

## Codex audit (verbatim)

1. **High — Motion off can show the wrong Pokémon and HP.** An in-memory check of a single forward step after a faint produced the departed sprite, its HP box, and an HP-loss overlay with Motion off. CSS cancels the animations that remove them, so the old box can cover the replacement until the next turn. Gate those temporary elements on the effective motion preference and hide any already mounted when Motion switches off. [review.ts:334](web/src/review.ts:334) · [style.css:610](web/src/style.css:610) · [style.css:817](web/src/style.css:817)

2. **High — Switching perspective makes the arrows skip turns.** “View as” rebuilds the screen and attaches another click handler to each existing arrow. I reproduced one Next click moving from step 1 to step 3 after a single swap. Bind the handlers once when the buttons are created. Give each arrow a `title` matching its existing `aria-label`. [review.ts:94](web/src/review.ts:94) · [review.ts:114](web/src/review.ts:114)

3. **High — A finished analysis can change the URL after the user leaves.** The poll checks whether the shared page container is connected. That container also hosts Games. In an in-memory navigation check, completion of the old review changed the Games URL back to the old replay, so reloading would reopen it. Dispose the review on route change, cancel its poll, and ignore late responses before rendering or writing history. [main.ts:16](web/src/main.ts:16) · [review.ts:231](web/src/review.ts:231) · [review.ts:351](web/src/review.ts:351)

4. **High — Pixel frames clip the keyboard focus ring.** Buttons, inputs, selects, and HP boxes clip to their border, while the focus outline sits 2 px outside it. Even on unclipped elements, yellow `#f5c032` measures only **1.51:1** against the light screen and **1.14:1** against the light page. Draw a two-tone inset indicator inside the pixel frame, with a dark edge on light surfaces and a light edge on dark controls. [style.css:86](web/src/style.css:86) · [style.css:89](web/src/style.css:89)

5. **High — Phone doubles leaves almost no width for HP boxes.** The phone rule fixes both sprites at 96 px. At a 320 px viewport, subtracting frames, padding, the eval bar, gaps, and sprite margins leaves roughly **32 px** for an HP-box column before its own padding. Clipped names and HP values are a layout hypothesis because the local server was unreachable. Give each side a sprite row and a full-width HP row at this width, retaining the eval bar beside the battle. [style.css:211](web/src/style.css:211) · [style.css:217](web/src/style.css:217) · [style.css:238](web/src/style.css:238)

6. **High — The sprite source breaks the official-art rule for newer species.** The renderer requests Gen 5 stills and animations for every species. The local cache includes Gholdengo, and Smogon identifies later-generation Black & White-style sprites as community artwork. Resolve each species and forme to a verified game asset, including its party mini. Use the species name when an official asset is unavailable. [battlefx.ts:43](web/src/battlefx.ts:43) · [sprites.py:70](server/sprites.py:70) · [Smogon sprite provenance](https://github.com/smogon/sprites#license)

7. **High — Rating changes, luck, and result letters lose contrast across themes.** In light mode, green `#3cc468` measures **2.03:1** for rating gains on `--screen` and **1.79:1** for luck on `--screen-2`. In dark mode, the white loss letter on `--them` measures **2.84:1**. Use separate text and fill colors. For example, light-theme green `#21643d` reaches **6.37:1** and **5.64:1** on those surfaces, and `#172238` reaches **5.59:1** on the dark loss badge. [style.css:174](web/src/style.css:174) · [style.css:181](web/src/style.css:181) · [style.css:368](web/src/style.css:368)

8. **High — Hover washes out the selected turn.** The hover selector outranks the current-turn selector for the background while the text stays white. In light mode that produces **1.26:1** contrast precisely when the pointer rests on the selected move. Apply the ordinary hover fill only to rows without `aria-current="step"`, and retain the selected row’s navy fill for hover and keyboard focus. [style.css:316](web/src/style.css:316) · [style.css:317](web/src/style.css:317) · [style.css:323](web/src/style.css:323)

9. **High — Crowded HP boxes silently hide battle conditions.** Boosts appear before Tera, confusion, and Leech Seed in a single nonwrapping, clipped row. At the default font size the chips are already 9.6 px, and the details card omits confusion and Leech Seed. A player can miss a condition that explains the turn. Reserve the HP number’s space, show a `+N` overflow indicator, and list every active condition in the details card. [review.ts:513](web/src/review.ts:513) · [style.css:677](web/src/style.css:677) · [style.css:883](web/src/style.css:883) · [battlefx.ts:123](web/src/battlefx.ts:123)

10. **Medium — The graph is far from the battle it explains.** The DS bottom screen contains Pokémon details. On a phone, the turn list and move-review panel both precede the graph. On desktop, the turn arrows also leave the hinge. Put the graph and turn selection directly below the hinge, keep the arrows there at every width, and place inspection and grading alongside on desktop or below on phones. [review.ts:121](web/src/review.ts:121) · [review.ts:131](web/src/review.ts:131) · [review.ts:152](web/src/review.ts:152)

11. **Medium — The UI offers actions that cannot succeed.** An unanalyzed VGC game offers “Grade every choice” until the server rejects it. The gallery also exposes Analyze and perspective switching against its synthetic `upload-gallery` ID. Have the analysis status response report eligibility before displaying the action, and give gallery mode an explicit set of supported controls. [review.ts:94](web/src/review.ts:94) · [review.ts:254](web/src/review.ts:254) · [jobs.py:25](server/review/jobs.py:25) · [gallery.ts:76](web/src/gallery.ts:76)

12. **Medium — Keyboard focus reaches Pokémon controls that do not activate.** HP boxes and sprite wrappers receive focus and respond to clicks, but Enter and Space do not pin them. Activating the dedicated pin also replaces the focused button. Use one native, named inspection button per Pokémon, expose its pressed state, and update the dedicated pin in place. [review.ts:388](web/src/review.ts:388) · [review.ts:423](web/src/review.ts:423) · [review.ts:518](web/src/review.ts:518) · [battlefx.ts:44](web/src/battlefx.ts:44)

13. **Medium — Losing one pixel of window height collapses the desktop workspace.** At 1366×620 the review uses three columns. At 1366×619 it switches to a single column capped at 820 px, separating the battle, turns, and analysis despite the available width. Choose columns by width and use height to control scrolling. Consolidate the repeated short-window rules, including the identical bottom-screen heights for singles and doubles. [style.css:77](web/src/style.css:77) · [style.css:393](web/src/style.css:393) · [style.css:833](web/src/style.css:833) · [style.css:851](web/src/style.css:851)

14. **Medium — The games refresh removes keyboard focus once a minute.** The background refresh replaces every game link even when the archive is unchanged. Someone tabbing through replays loses the focused link and their place. Preserve existing rows by game ID and update changed rows in place, restoring focus by ID if replacement is necessary. [list.ts:116](web/src/list.ts:116) · [list.ts:223](web/src/list.ts:223)

15. **Medium — Touching the graph commits a turn before the gesture is clear.** The plot seeks on `pointerdown` and sets `touch-action: none`, so a swipe begun there changes the turn and prevents vertical scrolling. Keyboard users can step globally, but the plot itself is exposed as a static image. Commit a seek on tap release, allow vertical panning and pinch zoom, and expose a focusable turn slider whose accessible value includes turn and win chance. [review.ts:612](web/src/review.ts:612) · [review.ts:636](web/src/review.ts:636) · [style.css:299](web/src/style.css:299)

## Claude audit (browser pane, measured 2026-11-23)

1. **High: light-theme focus ring is nearly invisible.** `--focus` `#f5c032` is one value for both themes (`web/src/style.css:27`); on the light screen it measures about 1.5:1 (needs 3:1). Same finding as Codex #4.
2. **High: green text fails in light mode.** `--hp-green` is used as text for `.delta.up` (+32 on the games list: 2.03:1), `.result-win`, `.turn-eval.up` (`style.css:181`, `:206`, `:321`). Dark-mode loss pip "L" is 2.84:1 (`style.css:174`). Same as Codex #7.
3. **High: phone doubles HP boxes are 87 px wide** at 375×812 (measured), so every name is cut to one letter ("P…", "S…"). Codex #5 predicted this from the code; measured here.
4. **Medium: turn rows cut the key event.** The Turns list shows one ellipsized line ("Palafin used Aqua Jet, Sinistc…") while the column has empty height below the last turn at 1440×900.
5. **Medium: two sets of turn arrows** on desktop (Turns header ◀ ▶ and the ← → pair at the list's foot).
6. **Medium: games list doesn't say which team is whose.** Each row shows a team under the opponent's name and another at the far right with no side marker or colour (`--you`/`--them` are used everywhere else).
7. **Low: tiny text.** Side tags 9.9 px and stat chips 9.6 px (`style.css:862-863`, `:878-883`); Codex #9 covers the chip overflow.
8. **Low: CSS layering.** The same media query `(min-width:1100px) and (min-height:620px) and (max-height:820px)` appears four times (`style.css:559`, `:832`, `:836`, `:850`); `.party-row` justify-content is set three times (`:219`, `:855`, `:859`); `.sprite.faint-now` and `.sprite.fainted` are each defined twice (`:588`/`:659`, `:235`/`:656`). Overlaps Codex #13.

Checked against Codex: Codex #2 (arrows skip turns after "View as") confirmed by reading `web/src/review.ts:113-114`: `build()` re-adds listeners to the reused `prevBtn`/`nextBtn` on every swap. Codex #1, #3, #11, #12, #14, #15 not reproduced by Claude (unverified).
