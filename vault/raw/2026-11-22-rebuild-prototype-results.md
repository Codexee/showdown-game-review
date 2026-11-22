---
title: Inputlog rebuild prototype results
type: raw
date: 2026-11-22
source: prototypes/inputlog-rebuild/rebuild.cjs, run in session 15119347 on data in data/proto/ (git-ignored)
---

# Inputlog rebuild prototype: results (raw)

Do not edit. Synthesized into [[ADR-0009-randbats-full-info-reconstruction]], [[spec-eval-model]] and [[open-questions]].

## Sample
- 60 newest `gen9randombattle` public replays (2 pages of `search.json?format=gen9randombattle`, ids 2717776712–2717795982), plus Codexe's fixture `gen9randombattle-2705718015`. 61 total.
- **All 61 had an inputlog.**
- `>version` commits: `ac7b7da0f9` (2026-11-13) × 59, `cbdc8519ef` (2026-10-27) × 1 (Codexe's Oct 28 game), `b557b5ed90` (2026-10-14) × 1. The `b557b5ed90` replay is `impulse-gen9randombattle-13297`, from a side server ("Impulse") that uploads to the same replay site with an id prefix.

## Method
- Blobless clone of smogon/pokemon-showdown; one `git worktree` per commit; `npm install --omit=dev && node build` (~5 s each; ~200 MB each with node_modules; 669 MB total for 3).
- `BattleStream` fed the whole inputlog; read `battle.log`; split channels with `extractChannelMessages` (from `dist/sim/battle.js`, not exported by battle-stream).
- Compare with the replay's `log` after dropping server-only lines. Teams from `battle.sides[i].team`.

## Findings
1. **Uploaded replay logs use the omniscient channel (-1):** exact HP for both sides (`253/253`), not the spectator percentages. The spectator channel (0) mismatched on the first `|switch|`.
2. Server-only lines that must be ignored when comparing: `j l n c c: t: raw html uhtml inactive inactiveoff badge title init` etc.; `||text` room messages (best-of-3 "X is ready for game 2."); `|-message|X forfeited.` (and the inactivity variant) just before `|win|`; `|player|pN|` lines after `|start` (empty = left the room, name = rejoined).
3. **Right commit: 61/61 exact matches** after those filters (first pass 17/61, all failures were the server lines above).
4. **Wrong commit:** each replay run at a different one of the three commits gave 56/61 matches. Visible failures: set levels changed between commits (Iron Thorns L81 vs L82, Swampert L82 vs L83, Brute Bonnet L79 vs L80 ×2) and a rule text change ("Pokémon" vs "Pokemon").
5. **Silent errors at the wrong commit:** 1 of the 56 wrong-commit "matches" had a different hidden set (Brute Bonnet level 79 → 80, a Pokémon that never switched in). **A log match only checks what was revealed, so the exact commit is required.**
6. Speed: 61 replays in 3.5 s with 3 Node processes (about 57 ms per replay including process start; much less per replay within one process).
7. Example (Codexe's Oct 28 loss, rebuilt at cbdc8519ef), opponent charizardslayer1's full team: Sawsbuck L88 Life Orb / Sap Sipper / Tera Ground (Swords Dance, High Horsepower, Horn Leech, Double-Edge); Baxcalibur L75 Choice Band / Thermal Exchange / Tera Dragon (Glaive Rush, Icicle Crash, Earthquake, Ice Shard); Glaceon L94 Heavy-Duty Boots / Ice Body / Tera Ground (Mud Shot, Freeze-Dry, Protect, Wish); Palafin L77 Choice Band / Zero to Hero / Tera Fighting (Wave Crash, Close Combat, Jet Punch, Flip Turn); Volbeat L90 Heavy-Duty Boots / Prankster / Tera Water (Roost, Thunder Wave, Encore, Lunge); Ampharos L88 Assault Vest / Static / Tera Fairy (Discharge, Dazzling Gleam, Volt Switch, Focus Blast).

## Side finding
- `server/ids.py` rejected 3-part replay ids such as `impulse-gen9randombattle-13297` and `smogtours-gen9ou-123`. Fixed the same day, with a test.
