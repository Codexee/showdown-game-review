---
title: Roadmap
type: spec
status: draft
tags: [area/vault]
updated: 2026-11-23
---

# Roadmap (draft)

The order follows the dependencies in [[architecture]]. Stages are not locked until the interview finishes ([[open-questions]]).

1. **Vault and repo.** This vault, git, project `CLAUDE.md`. *Done 2026-11-22.*
2. **Replay sync and archive.** *2a and 2b built 2026-11-22 ([[module-map]]); 2b still needs one real-browser test.* (a) Poller for `Codexe`'s new uploaded replays, plus the archive, game list, URL paste and file upload. (b) Userscript that sends every finished battle. Useful by itself. The same scraper also collects `gen9randombattle` training data. [[spec-replay-sync]], [[ADR-0006-replay-archive]]
3. **Log parser.** Protocol log → battle state per turn, from each side's view. *Done 2026-11-22: 99.4% of turn states exact on unseen games, 100% after fixes ([[battle-parser]]). Doubles unverified.*
4. **Review app shell.** Game list plus replay player with a placeholder eval (for example, remaining HP). Pixel-art style. [[spec-review-app]], [[visual-style]] *Done 2026-11-22 ([[ADR-0011-review-screen-battle-view]]).*
5. **Eval model, Gen 9 Random Battle.** Small test training, then the overnight run. Plug into the eval bar. [[spec-eval-model]] *Pipeline built 2026-11-22; test model installed (66% vs 64% on future games); overnight run pending.* *P0 upgrades done; full run `main` installed 2026-11-22 (67.4% vs 62.9% on future games, [[2026-11-22-main-run-results]]).*
6. **Move review.** Best move, labels such as "mistake", win chance after each choice. *Design from the benchmark: regret over a simulator-backed choice matrix with our value as the leaf; 5/10/20 bands; decision vs luck; luck ledger; accuracy score ([[benchmark-best-in-class]]).* *Built 2026-11-22 ([[ADR-0014-move-review-method]], [[2026-11-22-stage6-results]]): matrix, bands, per-turn luck, accuracy, review UI. Not yet: per-event luck ledger, hidden-item softening.* *Sampled worlds built 2026-11-22 ([[ADR-0015-move-review-sampled-worlds]]); unseen opposing species still real.*
7. **Model testing (current stage; closes after the overnight run `v12`, [[ADR-0018-grade-quality-before-ui]]).** v1.2 tests done ([[2026-11-23-v12-tests-and-eval-gains-results]]); two-view scoring and the search-blended eval bar built ([[ADR-0016-two-view-scoring-strict-gate]], [[ADR-0017-eval-bar-search-blend]]); `v12` started 2026-11-23 03:56 ([[plan-run-v12]]). No more training tests in this stage.
8. **Grade quality** ([[plan-grade-quality]], [[ADR-0018-grade-quality-before-ui]]). A verdict bank to score the move review against; the worlds fairness fix (dice averaged inside each cell, one strategy for the graded player across worlds; [[2026-11-23-codex-review]] finding 6); a depth-2 re-check of flagged choices that can acquit, never convict. Also from Codex finding 7: audit every Tera and switch choice; reconsider unconditional "no blame".
9. **Back to the UI.** Includes **importing the player's own team for every format where players build teams** (VGC first; the paste box already shows for them, [[2026-11-23-turn-motion-and-team-paste]]; not for Random Battle, whose teams are random) ([[2026-11-22-direction-codex-review]]). Codex's design notes: show the form only for VGC, parse and check the team, bind it to a side, record where each fact came from (paste, sheet, reveal, usage), pass it to the eval and the grader, and mark cached analysis stale when the team changes ([[2026-11-23-codex-review]] finding 9).
10. **VGC 2026 Reg M-C.** Doubles parser and model. [[ADR-0002-format-order]] VGC differs from Random Battle: **team preview picks** (bring 4 of 6) are a graded choice too; the opponent's sets are predicted from **usage stats**, not random-set data; each format has its own gimmick ([[2026-11-22-direction-codex-review]]). Check the open Champions engines (Mew's Truck, Ninjask) before writing one ([[2026-11-23-codex-review]] finding 8, unverified).
11. **Endgame goals** ([[goals-endgame]], set by the user 2026-11-23): depth-2 and MCTS search faster than PS Dashboard; usage-stat set guessing, EV spreads from damage, Scarf from move order; flagged mistakes re-searched one deeper; exact endgame solver at ≤3 a side; hidden-item softening; a fast VGC simulator; self-play last.

## Related
- [[index]] · [[project-overview]]
